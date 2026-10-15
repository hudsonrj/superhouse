# Migracao do Companion Life

## Reutilizar

- tipos de apoio e niveis de intervencao;
- estados do ciclo: ativo, pausado, discreto, aguardando apoio, estavel e
  encerrado;
- sequencia de seguranca, intensidade, capacidade, contexto, acao, check-in,
  contato humano e resumo;
- controles permanentes de voltar, pausar, silencio, orientacao e encerramento;
- persistencia minima do perfil e do ciclo na NVS;
- acoes locais e fluxo de emergencia independentes de rede ou IA.

## Refazer para esta placa

- telas em LVGL para o ST7789 320x240;
- entrada pelo FT5x06, sem calibracao manual do touch;
- texto falado como alternativa aos toques, iniciado pelo usuario;
- resposta por alto-falante com volume configuravel e opcao de silencio;
- previa de camera e indicador de consentimento;
- pagina de diagnostico para tela, toque, camera, microfones e alto-falante.

## Novos estados multimodais

1. pedido de uso do sensor e finalidade;
2. consentimento local e temporario;
3. captura unica ou trecho de voz;
4. processamento sem persistencia do conteudo bruto;
5. resultado observavel com incerteza;
6. confirmacao, correcao ou descarte pelo usuario;
7. retorno ao ciclo deterministico.

Camera e voz enriquecem o contexto, mas nunca pulam a pergunta de seguranca nem
alteram sozinhas o nivel de intervencao.
