## Ticket

Closes #<!-- número del issue -->

## Qué cambia

<!-- Resumen del cambio y el motivo. Si toca reglas de negocio, citar RN-xx. -->

## Cómo probarlo

<!-- Pasos concretos: comandos, datos de prueba y resultado esperado. -->

## Definición de hecho (AGENTS.md)

- [ ] Criterios de aceptación del ticket cumplidos.
- [ ] Reglas/RN aplicables respetadas.
- [ ] Un solo módulo tocado (o doble toque acordado y avisado antes de implementar).
- [ ] Tests nuevos para la lógica de negocio y suite completa en verde.
- [ ] `pytest -q`, `ruff check .` y `mypy app` en verde (si se tocó backend).
- [ ] `npm test -- --run`, `npm run lint` y `npx tsc --noEmit` en verde (si se tocó frontend).
- [ ] Sin números de negocio hardcodeados.
- [ ] Aislamiento de módulos respetado.
- [ ] Dinero con `Decimal` o centavos (nunca `float`).
- [ ] Permisos correctos por rol, con default denegar.
- [ ] Escrituras críticas idempotentes (si aplica).
- [ ] Spec actualizada si cambió una regla.
- [ ] Sin secretos, `.env`, `.db` ni el Excel real en el diff.

## Notas para el reviewer

<!-- Opcional: decisiones discutibles, deuda técnica o puntos que conviene mirar primero. -->
