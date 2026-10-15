# Desenvolvimento, atualização e backup

## Onde alterar

Use `C:\repositorio\superhouse` como cópia Git consolidada. As pastas antigas continuam sendo instalações de execução, e algumas ainda têm Git próprio. Uma alteração feita nelas não aparece automaticamente no monorepositório. Antes de commit/push, confirme o diretório:

```powershell
Set-Location C:\repositorio\superhouse
git rev-parse --show-toplevel
git status --short --branch
git remote -v
```

O remoto consolidado é `https://github.com/hudsonrj/superhouse.git`. Não envie um commit da instalação antiga do teclado presumindo que o layout remoto ainda tenha os arquivos na raiz.

## Mapa para mudanças

| Mudança | Onde investigar |
|---|---|
| Atalho, modificador, sentido de giro | `teclado2/global_shortcuts.py`, `test_nino_shortcut.py` |
| Janela de texto/voz | `teclado2/control/main.js`, `preload.js`, `renderer.js` |
| Indicador flutuante | `teclado2/control/autonomy-overlay.*` |
| Escala/política de autonomia | Cliente `autonomy.js`, servidor `server-autonomy.py`, indicador web e testes |
| Roteamento local/remoto do Nino | `nino/src/main/chat.js`, `ch8.js`, `ponte.js`, `hermes.js` |
| API Atom/sensor | `nino/src/server/atom.js`, `absence.js` e firmware Atom |
| Tela/protocolo CYD | `atlas_lvgl.ino`, `placa_gateway.py`, `cyd_api.py` |

Há um `AGENTS.md` na placa com orientações para uso de Graft. O cache `graft/` é local e foi excluído da importação. Se a ferramenta estiver instalada, comece por `graft map`; sem ferramenta/grafo, use os arquivos e os limites de evidência registrados nos manuais. Não trate um grafo ausente como uma descrição atual do código.

## Testes disponíveis

Execute a partir do diretório indicado. Estes comandos são verificações; não são instaladores.

### Teclado2

```powershell
Set-Location C:\repositorio\superhouse\teclado2
python test_nino_shortcut.py
node control\test-autonomy.js
python control\test-server-autonomy.py
python control\test-find-index.py
```

Os testes cobrem reconhecimento de teclas, modificadores, repetição, ordem de abertura das URLs, escala −3…+3, permanência do modo ligado em nível negativo, expiração, deduplicação e autenticação. Não pressionam o dispositivo físico.

```powershell
node control\run-ui-test.js
```

Esse teste usa Electron e serviços simulados para interface, áudio, entrada de texto, indicador e proteção de IPC. No código atual ele usa o Electron instalado em `C:\repositorio\nino`; ajuste o ambiente antes de executá-lo em outra máquina.

`test-live.js` faz integração real e pode transmitir uma pergunta. Leia antes de rodar; testes com “live” não são necessários para validar apenas documentação ou uma alteração estática.

### Nino

```powershell
Set-Location C:\repositorio\superhouse\nino
node scripts\test-absence.js
node scripts\test-presence.js
node --test scripts\test-atom.js
node scripts\test-ch8.js
node scripts\test-ponte.js
node scripts\test-hermes-routing.js
```

Há testes adicionais de modelo, Google, JEV, Hermes e gateway. Alguns dependem de instalações/credenciais externas. Revise os arquivos antes de ampliar a execução; não exponha conteúdo de e-mail em um teste de infraestrutura.

### Placa

O Atlas-server opcional possui testes Node em seu próprio diretório:

```powershell
Set-Location C:\repositorio\superhouse\placaamarelajarvis\companion2\atlas-server
npm test
```

Um teste de Atlas não comprova o firmware CYD. Compilação, USB, touch, Wi-Fi, microfone e alto-falantes exigem verificação própria e, em parte, hardware real.

## Atualizar sem perder configurações

1. Identifique quais diretórios realmente executam os serviços e qual commit está em produção.
2. Faça backup privado de configurações, credenciais, estado e dados necessários.
3. Atualize a cópia consolidada com a árvore limpa. `git pull --ff-only` evita uma mesclagem implícita inesperada.
4. Revise o diff e rode testes proporcionais à mudança.
5. Se a execução continuar nas pastas antigas, copie **somente os fontes alterados** para os destinos corretos. Não espelhe apagando `data/`, `vendor/`, `.git` ou dependências locais.
6. Reinicie os processos que mantêm o código em memória. Cliente Electron e servidor remoto podem precisar de reinícios separados.
7. Faça um teste sem ações externas e confirme estado/versão. Só depois retome automações.

Este repositório não tem um publicador único para todas as instalações. A sincronização entre cópia Git e diretórios de execução é uma etapa operacional explícita. Documente-a no registro da atualização.

## Mudança de protocolo

Ao alterar uma escala ou contrato, atualize produtor, consumidor, validação, testes e documentação. A migração para `scaleVersion: 2` mostrou por que isso é necessário: um servidor com nível −3 não pode ser interpretado pelo cliente antigo que só aceitava 0…3.

Não use o indicador otimista como autoridade de permissões. A API confirmada, a revisão e a validade precisam permanecer parte do protocolo. Ao reimplantar o servidor de autonomia, preserve o banco e confira o estado antes de reativar.

## Backup

| Tipo | Exemplos | Estratégia |
|---|---|---|
| Fontes | Componentes, documentação, lockfiles | Git e revisão de segredos antes do push |
| Segredos | Tokens, cofre Nino, Wi-Fi, kiosk | Cofre/backup privado com controle de acesso |
| Dados do usuário | Documentos, KB, áudio, diário | Política de retenção e cópia privada separada |
| Estado remoto | SQLite autonomia e configuração dos serviços | Snapshot consistente/backup do servidor |
| Recursos baixáveis | Modelos, vozes, ambientes | Manifestar versões e procedimento de reinstalação |
| Firmware anterior | Imagem/dispositivo antes de gravar | Backup privado quando aplicável, identificando modelo/partições |

O Git não é backup desses dados excluídos. Um clone novo não restaura permissões nem autenticações dos serviços. Dumps de flash podem conter credenciais e não devem ser adicionados ao repositório só para completar uma cópia.

## Qualidade da documentação

Ao alterar comportamento, atualize a tabela de atalhos, o diagrama/contrato correspondente e as instruções de teste. Use links relativos que funcionem no GitHub e Markdown com Mermaid. Diferencie “o código solicita” de “o serviço remoto executou”.

Não transforme nomes de pastas vazias em especificações inventadas. Para incluir Atom2/ESP32/House de fato, obtenha os fontes, o hardware-alvo, os arquivos de build e um procedimento de instalação verificável.
