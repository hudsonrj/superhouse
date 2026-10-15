# Manual do Superhouse

Esta documentação explica o código presente neste repositório e a instalação Windows observada na integração. Não presume que um clone tenha modelos, senhas, servidores remotos ou firmware gravado. Esses itens são instalados ou configurados separadamente.

## Roteiros de leitura

| Perfil / tarefa | Ordem sugerida |
|---|---|
| Entender o projeto | [Arquitetura](ARQUITETURA.md), [fluxos](FLUXOS.md), [estado real](ESTADO-IMPLEMENTACAO.md) |
| Instalar em outro computador | [Instalação](INSTALACAO.md), [configuração](CONFIGURACAO.md), [operação](OPERACAO.md) |
| Resolver um problema agora | [Diagnóstico](DIAGNOSTICO.md), depois o manual do componente |
| Desenvolver ou assumir manutenção | [Arquitetura](ARQUITETURA.md), [contratos](CONFIGURACAO.md), [desenvolvimento](DESENVOLVIMENTO.md) |

## Manuais dos componentes

- [Nino](../nino/GUIA-SUPERHOUSE.md): núcleo de conversa, voz, integrações e Atom Voice.
- [Teclado2](../teclado2/README.md): atalhos, interface Control e autonomia.
- [Placa Amarela/Jarvis](../placaamarelajarvis/GUIA-SUPERHOUSE.md): firmware, gateway, voz e variantes.
- [ESPClaw](../espclaw/README.md): referências de agendamento; projeto incompleto.
- [Atom2](../atom2/README.md), [ESP32](../esp32/README.md) e [House](../house/README.md): inventário e lacunas.

## Convenções

**Implementado** significa encontrado nos fontes. **Validado por teste** significa coberto por uma verificação automatizada, possivelmente com serviços simulados. **Validado no ambiente** refere-se à integração usada na máquina original. Nenhuma dessas expressões comprova uma instalação nova ou um dispositivo físico diferente.

Trechos de PowerShell são executados no Windows. Caminhos com `C:\repositorio` refletem a instalação atual. `<...>` identifica um valor a preencher, nunca uma credencial utilizável. Instruções de flash substituem firmware; instruções de instalação remota alteram serviços existentes. Leia as pré-condições antes de executá-las.

Os documentos antigos dos componentes foram preservados. Quando um guia antigo e estes manuais divergirem, compare com o arquivo de implementação indicado. Exemplos históricos de rede, usuário Windows e modelo não são padrões universais.

## Glossário

| Termo | Significado neste projeto |
|---|---|
| Control / CH8 | Serviço remoto de chat, ações, contexto e estado de autonomia; não é o modelo local |
| Ponte | Webhook autenticado que recebe instruções destinadas aos agentes |
| GrokBot | Agente externo mencionado nas instruções da ponte; seus canais e acessos não são implementados integralmente aqui |
| Gateway | Processo que adapta uma interface local ao protocolo de outro serviço |
| STT / Whisper | Conversão de áudio em texto, no computador |
| TTS / Piper | Conversão de texto em áudio, no computador |
| RAG / base local | Recuperação de trechos de documentos para contextualizar a conversa |
| Atomic Chat | Aplicativo externo que pode disponibilizar um modelo por API local compatível com OpenAI |
| Ollama | Alternativa de API local; o nome do módulo `ollama.js` também é usado para falar com Atomic Chat |
| Atom Voice | Dispositivo com firmware em `nino/firmware/atom-voice`; não confundir com a pasta vazia `atom2` |
| CYD | Cheap Yellow Display ESP32-2432S028R, placa com tela de 320×240 |
| Heartbeat | Mensagem periódica para indicar que um cliente ou sensor continua disponível |
| Lease | Autorização temporária; expira se não for renovada |
| Revisão | Número que identifica uma versão do estado de autonomia |
| Autonomia | Política de supervisão de respostas, separada do estado ligado/desligado |

## Como os documentos foram conferidos

As explicações usam caminhos e contratos do código importado. Há diagramas de arquitetura, hierarquia de decisão, implantação e sequência. Os comandos de teste disponíveis e as lacunas de instalação estão registrados; esta revisão documental não reinstala servidores, não grava placas e não comprova entregas em canais externos.
