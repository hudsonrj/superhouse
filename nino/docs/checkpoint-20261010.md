# Ponto de retorno — Nino, Control e agente da ponte

Confirmado em 10/10/2026. Tag: `nino-checkpoint-20261010`.

## Estado preservado

- Nino Electron no NoteAlliedIT, iniciado por `Nino.bat`.
- Atomic Chat pela API local em `127.0.0.1:1337/v1`, com descoberta do modelo ativo.
- Whisper local e Piper Windows; respostas de voz no computador.
- Atom Voice na COM20, áudio pela LAN e sensor PIR GPIO32.
- “CH oito, …” consulta o Control pelo adaptador privado Tailscale.
- “Ponte, …” envia a pergunta ao webhook da rotina; o agente retorna com `scripts/nino-speak.js`.

## Verificação deste checkpoint

Os testes de áudio/autenticação, presença, término do stream Atomic Chat, Control, webhook e prevenção de duplicação do gateway passaram. O ciclo real webhook → agente → Nino exibido e falado já foi registrado; a audibilidade foi confirmada pelo usuário.

O usuário confirmou sensor, botão e resposta funcionando após o teste físico. O monitor COM20 registrou os cliques e o início de gravação após reiniciar o Atom; a conexão Wi-Fi recebeu IP 192.168.15.2. Antes do reinício, os cliques eram registrados sem iniciar gravação. A confirmação de funcionamento inclui o relato do usuário, além dos testes de software.

Limitações conhecidas: o firmware pausa a leitura de presença enquanto envia/processa a gravação; cores do LED e reprodução no alto-falante do Atom ainda não foram confirmadas como corretas. A saída verificada é o computador. O SD não foi habilitado.

## Configuração privada

`data/checkpoints/nino-checkpoint-20261010/private.dpapi` guarda, criptografados pelo Windows, os arquivos de configuração do Atom/Control/webhook, os ajustes locais, o arquivo de segredos do firmware e os três binários do último build. O backup foi descriptografado em memória e validado por hash. Ele só pode ser aberto pelo mesmo usuário Windows; mantenha esse perfil e esse arquivo.

O backup é ignorado pelo Git. A tag/commit preserva código; o arquivo privado preserva a configuração e os binários com credenciais. O binário é do último build preservado, não uma extração da flash do aparelho.

## Voltar após adicionar funcionalidades

Primeiro preserve as alterações novas em outro commit/branch e encerre Nino e o serviço de voz. Então, com o diretório de trabalho limpo, crie uma branch a partir do ponto de retorno:

```powershell
git switch -c restaurar-nino nino-checkpoint-20261010
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/checkpoint-private.ps1 -Name nino-checkpoint-20261010 -Restore -WhatIf
```

O segundo comando apenas mostra os arquivos que seriam restaurados. Para restaurar de fato, rode novamente sem `-WhatIf`. Isso sobrescreve as configurações atuais, mas não grava firmware no Atom nem altera serviços remotos.

Reabra `Nino.bat` e `Nino-Atom.bat`. Se o firmware ou o adaptador remoto também tiverem sido alterados, será necessário restaurá-los separadamente usando os artefatos/código deste ponto; não afirmar que voltar o Git reverte esses dispositivos automaticamente. Dependências Windows instaladas permanecem no disco e não estão incluídas nesse pequeno backup.
