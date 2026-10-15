# Seguranca e privacidade

## Regras obrigatorias

- A menor intervencao que aumenta seguranca, clareza ou autonomia vem primeiro.
- Camera, microfone, previsoes e armazenamento possuem consentimentos separados.
- A ausencia de resposta nao significa melhora.
- Imagem e voz sao sinais auxiliares e faliveis.
- Estado emocional deve ser perguntado ao usuario, inclusive quando ha sinais
  visuais ou vocais aparentemente claros.
- O dispositivo nao reconhece identidade facial.
- O dispositivo nao faz vigilancia continua.
- Nenhum modelo pode alterar o fluxo local de emergencia ou recomendar mudanca
  de medicamento.
- O firmware inicia em modo local, sem servidor publico, telemetria, OTA ou
  transmissao de sensores.
- Habilitar rede nao concede automaticamente acesso a camera, microfone,
  historico ou contatos; cada finalidade exige permissao separada.

## Retencao padrao

- quadro de camera: memoria temporaria, descartado apos a requisicao;
- audio: transmitido durante a sessao, sem gravacao local;
- transcricao: nao persistida ate consentimento especifico ser implementado;
- perfil e ciclo: persistencia local minima e apagavel;
- telemetria: desabilitada por padrao.

## Resposta visual

Para bem-estar, a resposta deve usar a sequencia:

1. fatos observaveis e neutros;
2. limitacao explicita da inferencia;
3. pergunta curta de confirmacao;
4. no maximo uma proxima acao.

Exemplo: `Vejo postura curvada e pouco movimento. Isso pode ter varias causas.
Voce se sente cansado, sobrecarregado ou nenhuma dessas opcoes?`

## Possivel emergencia

A camera nao confirma que uma pessoa esta segura. Quando houver relato ou sinal
de risco imediato, o fluxo prioriza pessoa de confianca e atendimento
presencial. O modelo nao conduz sozinho uma crise grave.
