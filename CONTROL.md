# Atalhos do Control

- **Ctrl + Alt + Shift + Win + T** abre a caixa de pergunta. Enter envia; Shift + Enter quebra a linha. A resposta aparece formatada.
- **Ctrl + Alt + Shift + Win + Q** inicia a gravação. Aguarde a indicação **Gravando**, fale segurando Q e solte para transcrever, consultar o Control e ouvir a resposta. A resposta também aparece escrita.
- **Shift + Win + C** abre https://control.ch8ai.com.br.
- **Shift + Win + Z** abre https://monitor.ch8ai.com.br/ e https://chcontrol.ch8ai.com.br/ no navegador padrão.

Q/T/A também aceitam Ctrl + Alt + Win sem Shift, conforme os sinais observados no macropad.

## Autonomia

- **Ctrl + Alt + Shift + Win + A** alterna o modo ligado/desligado.
- **Ctrl + Alt + +** aumenta o nível somente quando ativo.
- **Ctrl + Alt + -** diminui o nível somente quando ativo.

Option corresponde a Alt no Windows. Os ajustes aceitam as teclas principais e as do teclado numérico. Essa ordem de aumento/diminuição foi definida pelo usuário.

O botão A liga/desliga; diminuir o nível não desliga. Escala: **-3**, aprovar cada etapa; **-2**, revisar rascunhos antes de enviar; **-1**, aprovar antes de responder; **0**, alertar e recomendar; **+1**, responder com confiança justificada de pelo menos 95%; **+2**, pelo menos 85%; **+3**, responder sem aprovação prévia, explicitando incertezas. A autorização abrange respostas nos canais já autorizados, não pagamentos, exclusões ou mudanças de acesso.

O indicador mostra imediatamente o nível solicitado, marcado como aguardando Control. A autorização efetiva só muda após confirmação do servidor. A escala exige atualizar o servidor com `control/install-autonomy.py`.

O servidor mantém o estado e uma autorização temporária de cinco minutos, renovada enquanto o cliente está ativo. Antes de responder, os agentes devem conferir o estado atual; estado inacessível, desligado ou expirado não autoriza envio. A aceitação pela ponte não comprova execução pelos agentes.

## Execução e diagnóstico

Execute `python global_shortcuts.py` neste diretório. Apenas uma cópia pode ficar ativa. Os registros ficam em `macropad.log` e `control-client.log`.

O cliente usa os módulos de transcrição, Control e voz instalados em `C:\repositorio\nino`. Para instalar a integração do servidor, execute `python control\install-autonomy.py`; a senha SSH é solicitada sem ser salva. Se solicitado, informe o caminho absoluto do arquivo HTML ativo no servidor, não o domínio nem apenas a pasta.
