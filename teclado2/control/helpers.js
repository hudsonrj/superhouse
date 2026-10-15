'use strict';
function validQuestion(text) {
  if (typeof text !== 'string' || !text.trim() || text.length > 8000) {
    throw new Error('Escreva ou grave uma pergunta de até 8000 caracteres.');
  }
}
function speechChunks(text) {
  if (typeof text !== 'string' || text.length > 200000) throw new Error('Resposta inválida.');
  // Cada trecho fica abaixo do limite do Piper, sem cortar o restante da resposta.
  return text.match(/[\s\S]{1,1200}(?:\s|$)|[\s\S]{1,1200}/g) || [];
}
module.exports = { validQuestion, speechChunks };
