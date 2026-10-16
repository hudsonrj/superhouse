# Estado de implementação e limites de evidência

Este inventário descreve a cópia disponível no monorepositório. Não é monitoramento em tempo real dos dispositivos nem garantia de que serviços externos estejam ativos.

| Componente | O que está disponível | O que falta para reprodução completa |
|---|---|---|
| Teclado2 | Ativador, interface Electron, voz/texto, indicador, autonomia, instalador remoto e testes | Dependências locais, caminhos/aliases do usuário, credenciais, modelos/vozes e servidor Control existente |
| Nino | Desktop/web, núcleo de conversa, STT/TTS, KB, integrações, servidor/firmware Atom, scripts | Modelos, binários Piper, venv, dados, credenciais e aplicativos externos |
| Placa Amarela/Jarvis | Firmware LVGL, gateway, API CYD, voz PC, variantes e documentação upstream | Token kiosk, Wi-Fi, toolchain/caminhos, preparação de build e hardware real |
| ESPClaw | Duas referências C do scheduler e armazenamento | Headers, projeto completo, toolchain/configuração-alvo e integração verificável |
| Atom2 | Diretório reservado | Fontes; a origem continha apenas `nul` |
| ESP32 | Diretório reservado | Fontes; a origem continha apenas `nul` |
| House | Diretório reservado | Fontes; a origem estava vazia |

## O que já foi validado na integração original

- Atalhos do teclado e sentido final do giratório foram ajustados com captura dos sinais e retorno do usuário.
- O cliente atualizado leu do Control o estado da escala negativa sem rejeitá-lo como inválido.
- O ativador foi cadastrado e observado em execução pela tarefa `CH8 Macropad`.
- A cópia consolidada foi enviada à `main`, preservando os fontes disponíveis e alterações locais dos componentes importados.

Esses fatos não equivalem a homologação em outra máquina, teste depois de todo reboot, validação de cada porta USB ou comprovação de todas as entregas a terceiros.

## Recursos implementados que dependem de fora

**Sensor de ausência:** o código atual sincroniza ativação neutra e prioridade manual com o Control. O registro de verificação física em 15/10/2026 relata firmware gravado na COM20, mas falha de autenticação/conexão Wi-Fi com motivo `WIFI_REASON_AUTH_EXPIRE`; não houve heartbeat confirmado nem validação física do ciclo de dez minutos. Isso está detalhado em [ausência e GrokBot](../nino/docs/ausencia-grokbot.md). Testes simulados ou de API não substituem essa pendência de hardware/rede.

**Conhecimento das empresas:** Q/T consultam o Control; a abrangência depende do contexto e das fontes realmente conectadas ao serviço. O código não comprova acesso universal a todos os projetos nem sincroniza todas as bases locais automaticamente.

**Agentes e canais:** o cliente manda políticas e eventos à ponte. Os agentes devem conferir a autonomia atual antes de responder. A implementação completa desses agentes/canais não está neste repositório; o aceite do webhook não comprova a aplicação da regra nem o envio ao destinatário.

**Hermes:** há rota local Nino e scripts de adaptação, mas o agente e seu ambiente são instalados fora deste repositório. A presença da rota não significa que Hermes esteja provisionado ou rodando como serviço.

**Sites Monitor/CHControl:** o atalho abre os endereços; seus backends e implantação completa não foram importados por essa ação.

**API CYD no servidor:** `cyd_api.py` referencia estado e arquivos da infraestrutura Control. Copiar esse script para um PC sem esses arquivos não reproduz a frota real.

## Dívidas operacionais importantes

1. Caminhos fixos Windows e endereços de rede ainda exigem adaptação.
2. Não existe instalador único de todos os componentes nem sincronização automática Git → instalações antigas.
3. O build LVGL contém caminhos de uma máquina e reaproveitamento de artefatos; uma compilação limpa precisa ser preparada e validada.
4. O gateway CYD desativa validação de certificado TLS em sua implementação atual. Isso não deve ser confundido com transporte externo endurecido.
5. Logs, diário e gravações não têm uma política universal de rotação/retenção.
6. Políticas de confiança dos agentes são instruções, não medições estatísticas calibradas por este código.
7. Há documentação histórica e variantes experimentais. O guia da integração prioriza os módulos atuais; o upstream genérico não prova suporte a cada placa no ambiente original.

## O que não foi feito nesta revisão documental

Não houve reinstalação do Windows, implantação remota, atualização de credenciais, gravação de firmware, abertura de firewall ou teste de mensagens reais em todos os canais. Essas verificações devem ser planejadas por componente usando [Instalação](INSTALACAO.md) e [Diagnóstico](DIAGNOSTICO.md).
