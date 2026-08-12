# Exportações ZIP assíncronas

Uma exportação é uma solicitação durável e temporária. O servidor valida os filtros já aprovados
por Documentos, grava a seleção naquele instante e enfileira `export.zip`. Documentos adicionados
depois da solicitação não entram no ZIP.

Estados visíveis: `pending`, `processing`, `available`, `partial`, `failed`, `expired` e
`excluded`. Somente `available` dentro das primeiras 24 horas pode ser baixado. `partial` e
`failed` mostram a contagem e o motivo seguro; nenhum estado incompleto é servido como ZIP
completo.

Operadores e Visualizadores só acessam suas próprias exportações. Administradores podem consultar
e baixar as exportações de outros usuários. Essa verificação ocorre novamente em cada listagem,
detalhe e download; respostas de acesso negado não revelam se outro usuário possui a exportação.

O worker lê cada artefato fiscal pelo owner de storage e confirma estado finalizado, digest e
tamanho antes de incluí-lo. Caminhos têm segmentos ASCII sanitizados e um sufixo determinístico
do documento para evitar traversal e colisões. O cleanup remove apenas o artifact lógico
`export_zip_temp`; a origem fiscal, evidências, cursores e estado de coleta permanecem intactos.

## Apresentação no navegador — P10-06

`ExportsSection` apresenta cada estado durável com rótulo e explicação em pt-BR. `pending` e
`processing` permanecem em acompanhamento, `complete` não libera download por si só, `available`
exige a URL vigente retornada pelo owner, e `partial`, `failed`, `expired` e `excluded` não são
tratados como ZIP completo. Expiração remove somente a ação de download e informa que o acervo de
origem permanece intacto.

Contagens, bytes e timestamps só são renderizados quando presentes na resposta; a UI não estima
percentual nem simula progresso local. Códigos `safe_error`, IDs, caminhos, conteúdo de documentos
e exceções internas são traduzidos para mensagens seguras ou omitidos. Uma falha de refresh mantém
a última leitura segura com estado stale explícito e retry. Solicitação, detalhe, retry e download
têm guards de interação; a listagem/detalhe posterior reconsulta o servidor e sequenciamento impede
resposta antiga de substituir uma seleção nova.
