# SerrebiTorrent em português (Brasil)

Esta tradução acompanha o trabalho de internacionalização do SerrebiTorrent e mantém o inglês como idioma-base e fallback.

## Estado da tradução

Já estão cobertos ou preparados para integração em pt-BR:

- Pesquisa de torrents, sites de pesquisa e indexadores;
- criação de torrents;
- Configurações da sessão local, incluindo seleção de idioma;
- Gerenciador de Conexões e edição de perfis;
- menus, sidebar, colunas e estados da janela principal;
- lista principal de torrents, incluindo estados de download e nomes acessíveis;
- documentação principal e instruções de build.

O seletor de idioma usa valores estáveis (`system`, `en` e `pt-BR`) para que a preferência não dependa do texto exibido na interface.

## Acessibilidade

A tradução preserva atalhos de teclado e mnemônicos (`&`) e inclui testes para evitar que futuras mudanças removam atalhos, placeholders ou valores dinâmicos das mensagens.

O suporte das listas virtuais foi separado em um componente reutilizável e possui testes para preservar o foco durante atualizações em segundo plano, evitando roubo de foco e perda da linha atual em leitores de tela.

A lista principal também foi separada para que estados, cabeçalhos e comportamento de foco possam ser validados independentemente da janela principal.

## Idiomas

- [English](README.md)
- Português (Brasil) — este arquivo
