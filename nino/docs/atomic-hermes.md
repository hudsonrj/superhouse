# Delegacao Atomic Chat para Hermes local

O conector MCP `hermes-local` expoe `hermes_delegate_task(task)` no Atomic Chat. A ferramenta inicia uma sessao do Hermes instalado no Windows, aguarda seu resultado estruturado e retorna texto, estado, job_id e session_id. O modelo do Atomic decide chamar a ferramenta para pedidos de acao; a ferramenta precisa estar habilitada na conversa.

O executor preserva o perfil e as permissoes do Hermes, sem `--yolo`. O Hermes atual usa Grok na nuvem: executor local nao significa inferencia local. As ferramentas de terminal/arquivos habilitadas no Hermes podem atuar com as permissoes do usuario. Esta integracao nao instala controle grafico adicional.

Configuracao: `python scripts/configure-atomic-hermes.py`. Usa o SDK Python ja instalado no ambiente Hermes; nao instala dependencias. Preserva os outros MCPs e guarda `mcp_config.before-nino-hermes.json` ao lado da configuracao privada do Atomic. O timeout global de ferramentas passa a pelo menos 300 segundos para aguardar a delegacao.

Se o Atomic ainda estiver usando a lista anterior, recarregue seus conectores ou reabra o aplicativo. Teste pedindo explicitamente: "Use hermes_delegate_task para consultar o nome deste computador, sem alterar arquivos, e traga o resultado."

Limites: uma tarefa por processo MCP, 12 iteracoes, orcamento de 180 segundos e teto externo de 240 segundos. Tarefas interrompidas nao sao repetidas automaticamente; alteracoes ja feitas permanecem. Registros privados ficam em `data/hermes/`. A capacidade de o modelo escolher/chamar ferramentas precisa de teste real na conversa.

Este conector atende o Atomic Chat. A API `/v1/chat/completions` nao herda os MCPs da interface Atomic; o Nino agora delega diretamente pelo executor compartilhado quando reconhece o pedido. A ponte existente para o agente na nuvem permanece separada.

Verificado em 10/10/2026: o cliente MCP encontrou a ferramenta, delegou uma consulta somente leitura e recebeu `NoteAlliedIT`, sessao `20261010_192325_ad5c76`. Foram testados entrada invalida, erro/ausencia de resultado e registro da ferramenta. Nao foram testadas alteracoes de arquivos ou controle grafico.

O teste da API do modelo ativo com escolha automatica tambem selecionou `hermes_delegate_task` com argumentos validos para um pedido de consulta no terminal. Esse teste nao executou outra tarefa. Ele verifica a selecao pelo modelo separadamente da execucao real pelo MCP; nao substitui testar uma conversa na interface do Atomic.

## Agentes e periodicidade pelo Nino

O caminho compartilhado de texto e voz aceita `Hermes, ...` e pedidos diretos como
`Crie um agente ...` ou `Agende uma rotina ...`. O resultado do Hermes retorna ao
mesmo caminho de resposta do Nino, incluindo a fala em conversas pelo Atom.
Outras ações precisam do prefixo Hermes; a classificação geral pelo Atomic ainda
depende do tempo de resposta e suporte a ferramentas do modelo.

O executor instrui o Hermes a consultar os perfis existentes antes de criar um
com `profile create --clone-from default --no-alias`, sem mudar o perfil padrão
ou copiar canais. Para recorrência, consulta as rotinas, evita duplicar tarefas
idênticas e usa o cron nativo do perfil padrão, com entrega no histórico local.
Ele deve conferir o ticker e devolver nome/id, intervalo e próxima execução.
Nenhuma rotina nova é criada sem pedido com tarefa e periodicidade.

Exemplos: `Hermes, crie um agente revisor para revisar este projeto`;
`Hermes, agende uma rotina para verificar o espaço do disco C a cada 2 horas`;
`Hermes, liste as rotinas e pause a rotina ID`.

O computador precisa estar ligado e o ticker do Hermes ativo. Rotinas perdidas
durante desligamento podem executar atrasadas. Cancelar a espera no Nino não
reverte ações já iniciadas; consulte o histórico antes de reenviar.
