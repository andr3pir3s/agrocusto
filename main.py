"""AgroCusto - controle de safra e custos para o pequeno produtor rural."""
import sys

from src import config, menus, servico


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # evita erro de acentos no Windows
    except AttributeError:
        pass

    config.carregar_env()  # lê o arquivo .env, se existir
    estado = servico.criar_estado()
    try:
        menus.tela_conexao(estado)
        menus.menu_principal(estado)
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Encerrado pelo usuário.")
    finally:
        if estado["conn"]:
            estado["conn"].close()
    print("\n  Até a próxima safra!")


if __name__ == "__main__":
    main()
