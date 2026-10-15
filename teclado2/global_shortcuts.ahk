#NoEnv
SetBatchLines -1
#SingleInstance force

; Atalhos globais para abrir aplicativos
; Funcionam em qualquer lugar do Windows

; Ctrl+G = Grok Bot
^g::
{
    Run, "C:\Program Files\Grok Bot\Grok Bot.exe"
    return
}

; Ctrl+O = ChatGPT
^o::
{
    Run, "C:\Program Files\WindowsApps\OpenAI.ChatGPT-Desktop_1.2026.190.0_x64__2p2nqsd0c76g0\app\ChatGPT Classic.exe"
    return
}

; Ctrl+K = Claude
^k::
{
    Run, "C:\Program Files\WindowsApps\Claude_1.49585.0.0_x64__pzs8sxrjxfjjc\app\claude.exe"
    return
}

; Ctrl+L = Cursor
^l::
{
    Run, "C:\Users\hudson.santos\AppData\Local\Programs\cursor\Cursor.exe"
    return
}

; Tooltip pra confirmar que está rodando
TrayTip, Mini Teclado, Atalhos configurados, 10
