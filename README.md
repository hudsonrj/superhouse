# Superhouse

Componentes do Superhouse reunidos em um único repositório.

| Diretório | Componente |
|---|---|
| [atom2](atom2/) | Pasta reservada; sem código disponível na origem nesta importação. |
| [esp32](esp32/) | Pasta reservada; sem código disponível na origem nesta importação. |
| [espclaw](espclaw/) | Referências C do agendador e armazenamento do ESPClaw. |
| [house](house/) | Pasta reservada; vazia na origem nesta importação. |
| [nino](nino/) | Assistente com interface, voz e integrações. |
| [placaamarelajarvis](placaamarelajarvis/) | Firmware, gateway e interface da placa amarela. |
| [teclado2](teclado2/) | Atalhos globais, consulta ao Control e ajustes de autonomia. |

## Uso

Consulte as instruções de cada componente. O teclado usa módulos do Nino, e os caminhos atuais do ativador apontam para `C:\repositorio\nino` e `C:\repositorio\teclado2`. Reunir os fontes aqui não altera automaticamente esses caminhos nem a inicialização do Windows.

Esta importação reúne os arquivos atuais dos diretórios originais, incluindo alterações locais. Os históricos independentes de Nino e da placa permanecem nos respectivos repositórios originais; o histórico anterior do teclado permanece neste repositório, agora dentro de `teclado2/`.

## Arquivos locais

Credenciais, tokens, configurações privadas, documentos pessoais, bases de conhecimento, gravações, logs, dependências instaladas, modelos de IA e dumps de memória não fazem parte deste repositório. Configure as credenciais na máquina de destino e instale as dependências conforme a documentação de cada componente. Modelos e ferramentas de voz/transcrição do Nino precisam ser instalados separadamente.

`atom2`, `esp32` e `house` não tinham fontes disponíveis na cópia local no momento desta importação; seus diretórios contêm apenas a indicação dessa situação.
