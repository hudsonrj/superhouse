#NoEnv
SetBatchLines -1
#SingleInstance force

; Mini Teclado - 4 Botões
; Abre aplicativos no computador

; OPÇÃO 1: Se as teclas forem F13, F14, F15, F16
F13::
{
    Run, "C:\Program Files\Grok Bot\Grok Bot.exe"
    return
}

F14::
{
    Run, "https://claude.ai"
    return
}

F15::
{
    Run, "https://chat.openai.com"
    return
}

F16::
{
    Run, "https://grok.com"
    return
}

; -----------------------------------
; OPÇÃO 2: Se as teclas forem 1, 2, 3, 4 (descomente se opção 1 não funcionar)
; Descomente as linhas abaixo e comente as acima

/*
1::
{
    Run, "C:\Program Files\Grok Bot\Grok Bot.exe"
    return
}

2::
{
    Run, "https://claude.ai"
    return
}

3::
{
    Run, "https://chat.openai.com"
    return
}

4::
{
    Run, "https://grok.com"
    return
}
*/

; -----------------------------------
; Dica: Se as teclas tiverem outros códigos, edite este arquivo
; e substitua F13, F14, F15, F16 pelos códigos corretos
