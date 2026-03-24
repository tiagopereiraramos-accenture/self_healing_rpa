from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from rpa_self_healing.domain.entities import ActionStatus
from rpa_self_healing.infrastructure.logging.rpa_logger import TransactionTracker


@dataclass
class StepResult:
    """Resultado de um step individual do pipeline."""

    step_name: str
    status: ActionStatus
    data: dict[str, Any] = field(default_factory=dict)


class Pipeline:
    """Orquestra steps de use cases em sequencia com branching por status.

    Cada step e um use case (classe com ``__init__(driver)`` e ``execute(**kwargs)``).
    O pipeline encadeia steps automaticamente: se um step falha, executa o
    error handler e interrompe (ou continua, conforme configurado).

    Uso basico::

        result = await Pipeline(driver, bot_name="meu_bot") \\
            .step("login", LoginUC) \\
            .step("coleta", ColetarDadosUC) \\
            .step("download", BaixarArquivoUC) \\
            .on_error(notificar_erro) \\
            .run(**kwargs)

    Uso com condicoes::

        result = await Pipeline(driver, bot_name="meu_bot") \\
            .step("login", LoginUC) \\
            .step("admin-check", AdminCheckUC, when=lambda r: r.get("role") == "admin") \\
            .step("coleta", ColetarDadosUC) \\
            .run(**kwargs)

    Uso com merge de kwargs entre steps::

        result = await Pipeline(driver, bot_name="meu_bot") \\
            .step("login", LoginUC, forward=["token", "session_id"]) \\
            .step("coleta", ColetarDadosUC) \\
            .run(username="user", password="pass")

    Cada step recebe os kwargs originais + os campos forwarded dos steps anteriores.
    """

    def __init__(self, driver: Any, bot_name: str) -> None:
        self._driver = driver
        self._bot_name = bot_name
        self._steps: list[_StepConfig] = []
        self._error_handler: Callable[..., Coroutine] | None = None
        self._stop_on_error: bool = True

    def step(
        self,
        name: str,
        uc_class: type,
        when: Callable[[dict[str, Any]], bool] | None = None,
        forward: list[str] | None = None,
    ) -> Pipeline:
        """Adiciona um step ao pipeline.

        Args:
            name: Nome do step (aparece nos logs e metricas).
            uc_class: Classe do use case (deve ter ``__init__(driver)`` e ``execute(**kwargs)``).
            when: Condicao opcional — se retornar ``False``, o step e pulado.
                  Recebe o resultado do step anterior como argumento.
            forward: Lista de chaves do resultado deste step que serao
                     injetadas como kwargs nos steps seguintes.

        Returns:
            O proprio pipeline (fluent API).
        """
        self._steps.append(_StepConfig(
            name=name,
            uc_class=uc_class,
            when=when,
            forward=forward or [],
        ))
        return self

    def on_error(
        self,
        handler: Callable[..., Coroutine],
        stop: bool = True,
    ) -> Pipeline:
        """Define handler chamado quando um step falha.

        Args:
            handler: Funcao async chamada com ``(step_name, result, driver)``.
            stop: Se ``True`` (padrao), interrompe o pipeline apos o erro.
                  Se ``False``, loga o erro e continua para o proximo step.

        Returns:
            O proprio pipeline (fluent API).
        """
        self._error_handler = handler
        self._stop_on_error = stop
        return self

    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """Executa todos os steps em sequencia.

        Returns:
            dict com: status, steps_completed, steps_skipped, steps_failed,
            results (lista de StepResult), healing_stats, ultimo resultado.
        """
        results: list[StepResult] = []
        forwarded_kwargs: dict[str, Any] = {}
        completed = 0
        skipped = 0
        failed = 0
        last_result: dict[str, Any] = {}

        with TransactionTracker(
            bot_name=self._bot_name,
            action="pipeline",
            item_id="|".join(s.name for s in self._steps),
        ) as tracker:
            for i, step_cfg in enumerate(self._steps):
                step_kwargs = {**kwargs, **forwarded_kwargs}

                # Verificar condicao
                if step_cfg.when is not None and not step_cfg.when(last_result):
                    logger.info(f"[PIPELINE] Step '{step_cfg.name}' pulado (condicao nao atendida)")
                    results.append(StepResult(
                        step_name=step_cfg.name,
                        status=ActionStatus.SUCESSO,
                        data={"skipped": True},
                    ))
                    skipped += 1
                    continue

                # Executar step
                logger.info(
                    f"[PIPELINE] Step {i + 1}/{len(self._steps)}: '{step_cfg.name}'"
                )
                try:
                    uc = step_cfg.uc_class(self._driver)
                    result = await uc.execute(**step_kwargs)
                except Exception as exc:
                    result = {
                        "status": ActionStatus.ERRO_TECNICO,
                        "msg": str(exc),
                    }

                status = ActionStatus(result.get("status", ActionStatus.ERRO_TECNICO))
                step_result = StepResult(
                    step_name=step_cfg.name,
                    status=status,
                    data=result,
                )
                results.append(step_result)
                last_result = result

                # Forward de campos para proximos steps
                for key in step_cfg.forward:
                    if key in result:
                        forwarded_kwargs[key] = result[key]

                if status == ActionStatus.SUCESSO:
                    completed += 1
                    logger.success(f"[PIPELINE] Step '{step_cfg.name}' concluido")
                else:
                    failed += 1
                    logger.error(
                        f"[PIPELINE] Step '{step_cfg.name}' falhou: "
                        f"{result.get('msg', status)}"
                    )
                    if self._error_handler:
                        try:
                            await self._error_handler(step_cfg.name, result, self._driver)
                        except Exception as handler_exc:
                            logger.error(f"[PIPELINE] Error handler falhou: {handler_exc}")

                    if self._stop_on_error:
                        tracker.fail(
                            f"Pipeline parado no step '{step_cfg.name}': "
                            f"{result.get('msg', status)}"
                        )
                        break

            tracker.add_data("steps_completed", completed)
            tracker.add_data("steps_skipped", skipped)
            tracker.add_data("steps_failed", failed)
            tracker.add_data("steps_total", len(self._steps))
            tracker.add_healing_stats(self._driver.get_healing_stats())

        final_status = ActionStatus.SUCESSO if failed == 0 else ActionStatus.ERRO_LOGICO

        return {
            "status": final_status,
            "steps_completed": completed,
            "steps_skipped": skipped,
            "steps_failed": failed,
            "steps_total": len(self._steps),
            "results": [
                {"step": r.step_name, "status": str(r.status), **r.data}
                for r in results
            ],
            "last_result": last_result,
        }


@dataclass
class _StepConfig:
    name: str
    uc_class: type
    when: Callable[[dict[str, Any]], bool] | None = None
    forward: list[str] = field(default_factory=list)
