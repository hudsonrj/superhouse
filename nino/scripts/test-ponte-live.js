'use strict';
// One real webhook request; the routine responds separately through nino-speak.js.
const { createChatSession } = require('../src/main/chat');
async function main() {
  const result = await createChatSession().ask('Ponte, teste de integração do Nino: verifique apenas se o Raspberry Pi está acessível, sem alterar configurações. Responda por voz no Nino com uma frase curta sobre o resultado.');
  if (!result.ok) throw new Error(result.error);
  console.log(result.text);
}
main().catch((err) => { console.error(err.message); process.exitCode = 1; });
