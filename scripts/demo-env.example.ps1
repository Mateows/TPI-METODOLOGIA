# Plantilla de credenciales del demo (LOCAL, nunca se versiona).
#
# Uso:
#   Copy-Item scripts/demo-env.example.ps1 scripts/demo-env.ps1
#   # editá scripts/demo-env.ps1 con las contraseñas de TU base local
#
# scripts/demo-env.ps1 está en .gitignore. Si no existe, los scripts
# `preflight-demo.ps1` y `demo-video.ps1` cortan con un mensaje claro.
#
# Los valores de abajo son placeholders: reemplazalos por los que uses en tu
# entorno. No los commitees ni los pases como argumento por línea de comandos.

$env:TPI_DEMO_PASSWORD_A          = "<password-del-admin-de-la-clinica-A>"
$env:TPI_DEMO_PASSWORD_B          = "<password-del-admin-de-la-clinica-B>"
$env:TPI_DEMO_PASSWORD_RECEPCION  = "<password-de-la-recepcionista>"
