# Inicializacao no Windows

A tarefa `Nino-Startup` do Agendador executa `scripts/start-windows.ps1` no login deste usuario, sem console visivel e sem elevar privilegios. Inicia Nino e o servidor Atom, espera o endereco LAN e evita iniciar outra copia do servidor na porta 3082. O instalador remove a antiga entrada Run do Nino para evitar duas partidas.

Atomic Chat ja tem sua propria inicializacao no Windows. `scripts/ensure-atomic.js` aguarda seu controle local autenticado, inicia a API caso esteja parada e carrega o modelo capturado na instalacao caso ainda nao esteja ativo. Nao cria outro servidor de modelos. A configuracao fica em `data/startup/atomic-model.json`; logs em `data/startup/`.

O carregamento frio do modelo pode levar varios minutos. A requisicao de carga aguarda ate dez minutos; a tarefa de startup tem teto de vinte minutos. Nino e servidor Atom iniciam antes dessa espera.

Para escolher outro modelo de retomada, carregue-o no Atomic Chat e rode `node scripts/ensure-atomic.js --capture`. Para remover a inicializacao do Nino: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/install-windows-startup.ps1 -Remove`.

A inicializacao exige login, esta pasta, Node/Electron e a instalacao atual do Atomic Chat. Nao instala Hermes como servico: ele ainda nao esta integrado ao Nino. Pi e agente da ponte sao servicos externos. Se o IP LAN mudar, atualize a configuracao do Atom e seu firmware quando necessario.
