# Guía de Estilo para Frontends de la Colmena

## Framework Obligatorio: Bootstrap 5
Todos los frontends DEBEN usar Bootstrap 5 para garantizar un diseño profesional, consistente y responsivo.

### Inclusión en HTML
El `<head>` del fichero HTML DEBE incluir el siguiente enlace al CSS de Bootstrap:
`<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">`

El `<body>` DEBE incluir el siguiente script de Bootstrap antes de cerrar la etiqueta `</body>`:
`<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>`

## Reglas de Componentes
- **Contenedor Principal**: El layout principal de la página DEBE estar envuelto en un `div` con la clase `.container` o `.container-fluid` para un centrado y márgenes adecuados.
- **Tablas**: Las tablas DEBEN usar las clases de Bootstrap: `.table`, y opcionalmente `.table-striped`, `.table-hover`.
- **Formularios**: Cada grupo de `label` e `input` DEBE estar envuelto en un `div` con la clase `.mb-3`. Los `input` y `select` DEBEN tener la clase `.form-control`. Los `label` DEBEN tener la clase `.form-label`.
- **Botones**: Todos los `<button>` DEBEN tener la clase base `.btn`.
  - Botones de envío/guardado: `.btn-primary`
  - Botones de eliminación: `.btn-danger`
  - Botones de edición: `.btn-warning`
  - Botones genéricos: `.btn-secondary`
- **Alertas y Mensajes**: Para mostrar mensajes de éxito o error al usuario, DEBES usar el componente "Alert" de Bootstrap con las clases `.alert`, `.alert-success` o `.alert-danger`.

## Atributos para Pruebas (data-testid)
Si el plan de construcción incluye un `contrato_qa_e2e`, DEBES añadir los atributos `data-testid` a los elementos HTML correspondientes con los valores especificados en dicho contrato.