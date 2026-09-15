# SerrebiTorrent em português (Brasil)

Esta tradução acompanha o trabalho de internacionalização do SerrebiTorrent e mantém o inglês como idioma-base e fallback.

## Estado da tradução

Já estão cobertos ou integrados em pt-BR:

- Pesquisa de torrents, sites de pesquisa e indexadores;
- criação de torrents;
- Configurações da sessão local, incluindo seleção de idioma;
- Gerenciador de Conexões e edição de perfis;
- menus, sidebar, menu de contexto e estados principais da janela;
- lista principal de torrents, incluindo cabeçalhos, estados de download e nome acessível;
- mensagens principais de conexão e diálogo Sobre;
- documentação principal e instruções de build.

O seletor de idioma usa valores estáveis (`system`, `en` e `pt-BR`) para que a preferência não dependa do texto exibido na interface. Da mesma forma, filtros internos como `All` e `Downloading` continuam usando valores canônicos independentemente dos rótulos `Todos` e `Baixando` mostrados na interface.

## Execução pelo código-fonte

A interface localizada usa `app_entry.py` como ponto de entrada. Para executar o SerrebiTorrent pelo código-fonte, use:

```powershell
python app_entry.py
```

O pacote gerado pelo PyInstaller usa o mesmo ponto de entrada, portanto a execução pelo código-fonte e a versão empacotada seguem o mesmo fluxo de localização.

## Acessibilidade

A tradução preserva atalhos de teclado e mnemônicos (`&`) e inclui testes para evitar que futuras mudanças removam atalhos, placeholders ou valores dinâmicos das mensagens.

O suporte das listas virtuais foi separado em um componente reutilizável e possui testes para preservar o foco durante atualizações em segundo plano, evitando roubo de foco e perda da linha atual em leitores de tela.

A lista principal extraída está integrada ao runtime localizado. Ela preserva seleção e foco por info hash durante atualizações e ordenação, usa cabeçalhos e estados em pt-BR e mantém os mesmos eventos de teclado, seleção, foco e menu de contexto usados pela janela original.

O fork também executa uma validação específica no Windows com Python 3.14: instala as dependências, importa o entry point localizado e executa a suíte de testes, além do gate existente no macOS.

## Idiomas

- [English](README.md)
- Português (Brasil) — este arquivo
