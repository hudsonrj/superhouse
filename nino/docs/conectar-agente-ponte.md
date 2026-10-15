# Acesso do agente da ponte ao Nino

O Nino roda no **NoteAlliedIT / Windows**, em `C:\repositorio\nino`.

## Comando recomendado no NoteAlliedIT

```powershell
node C:\repositorio\nino\scripts\nino-speak.js "Olá, Hudson. Esta mensagem veio do agente da ponte."
```

O comando lê a autenticação local, envia a mensagem à API do Nino e só retorna sucesso depois da exibição e reprodução pelo Windows. Não imprime a chave. Não precisa de MCP nem de trocar o diretório atual.

## API HTTP

Endereço LAN: `http://192.168.15.3:3082`.

`POST /speak`, `Content-Type: application/json`, `Authorization: Bearer <chave local>`, corpo `{"text":"Mensagem do agente"}`. Texto de 1 a 2000 caracteres. A chave fica no campo `token` de `C:\repositorio\nino\data\atom-config.json`, fora do Git. Não colocar o valor em mensagens ou comandos compartilhados.

Sucesso: HTTP 200, `{"ok":true,"output":"pc"}`. HTTP 401 significa falta de autenticação; 409 indica conversa em andamento; 503 indica falha na exibição ou áudio. Em caso de erro, não repetir automaticamente: a mensagem pode já ter aparecido.

O Raspberry Pi alcançou esse endereço e recebeu HTTP 401 no teste sem chave, confirmando conectividade e proteção da rota. Esse IP é da LAN; não afirmar que a porta 3082 escuta no endereço Tailscale do NoteAlliedIT. Um agente na nuvem pode usar seu acesso existente ao terminal do NoteAlliedIT para executar o comando acima.

Essa rota apresenta e fala a mensagem pronta do agente. Não executa comandos nem consulta o Atomic Chat. O caminho inverso usa o webhook descrito abaixo.

## Pergunta do Nino para a Ponte — webhook

O agente criou a rotina “Pergunta do Nino para a Ponte”, disparada por webhook com corpo `{"text":"sua pergunta"}`. O conector está implementado em `src/main/ponte.js`, usando URL e autenticação fornecidas pelo usuário e armazenadas somente na configuração privada.

Configuração privada em `data/ponte-config.json`, ignorada pelo Git. Para preencher localmente sem exibir a URL/chave no terminal:

```powershell
python C:\repositorio\nino\scripts\configure-ponte.py
```

Informar a URL completa, o nome exato do cabeçalho e seu valor completo conforme a aba Routines. O configurador não dispara a rotina. O teste real só deve ocorrer depois de verificar esses dados.

Uso preparado: “Ponte, verifique o Raspberry Pi”, ou `/ponte verifique o Raspberry Pi`. Apenas a pergunta vai no POST; não enviar histórico, documentos ou credenciais locais. Um HTTP de sucesso confirma recebimento, não conclusão da tarefa. O Nino informa que a pergunta foi enviada, e o agente responde depois com `nino-speak.js`. Não reenviar automaticamente em caso de timeout, pois a rotina pode ter recebido o pedido.

O prefixo CH8 continua usando a conversa do Control. O prefixo Ponte usa a rotina do agente; não substituir um pelo outro silenciosamente.

### Configuração ativada

O webhook da rotina foi configurado em 10/10/2026 com o cabeçalho Authorization Bearer fornecido pelo usuário. URL e chave estão somente na configuração privada, não neste documento. Nino e serviço de voz foram reiniciados com o conector ativo. O teste real enviou uma pergunta para verificar o acesso ao Pi sem alterar configurações e recebeu confirmação HTTP de sucesso do webhook. Essa confirmação não significa que o agente concluiu a execução; a resposta deve chegar separadamente pelo comando `nino-speak.js`.

O serviço registra `[Nino] Mensagem do agente exibida e falada.` após completar uma resposta recebida pelo endpoint `/speak`, sem imprimir a chave nem o texto da mensagem.

O ciclo real foi confirmado: a rotina recebeu a pergunta de teste, e o serviço do Nino registrou a mensagem de retorno exibida e falada. Foi criado o áudio da resposta em 10/10/2026 às 11:49:46, horário local. O usuário já havia confirmado audibilidade do caminho agente → Nino anteriormente.

Outras rotas existentes: `POST /presence` abre a conversa; `POST /voice` recebe WAV PCM mono 16 bits/16000 Hz do Atom. Todas exigem autenticação. Nenhum servidor MCP do Nino foi implementado.
