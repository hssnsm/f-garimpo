"""Comandos de terminal para varrer imagens, listar plugins e iniciar a interface web."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from garimpo import __version__
from garimpo.config import ScanConfig
from garimpo.logging_config import setup_logging
from garimpo.plugins import list_plugin_info, FORMAT_ALIASES
from garimpo.recovery import RecoveryEngine
from garimpo.reports import write_reports
from garimpo.utils import parse_size, human_size, platform_name

_console = Console()


_BANNER = r"""
 ██████╗  █████╗ ██████╗ ██╗███╗   ███╗██████╗  ██████╗
██╔════╝ ██╔══██╗██╔══██╗██║████╗ ████║██╔══██╗██╔═══██╗
██║  ███╗███████║██████╔╝██║██╔████╔██║██████╔╝██║   ██║
██║   ██║██╔══██║██╔══██╗██║██║╚██╔╝██║██╔═══╝ ██║   ██║
╚██████╔╝██║  ██║██║  ██║██║██║ ╚═╝ ██║██║     ╚██████╔╝
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝     ╚═╝╚═╝      ╚═════╝
"""
_TAGLINE = "Escave o invisível. Recupere o impossível."


def _print_banner() -> None:
    _console.print(f"[bold cyan]{_BANNER}[/bold cyan]")
    _console.print(f"[dim]  {_TAGLINE}[/dim]")
    _console.print(f"  [dim]v{__version__} | {platform_name()}[/dim]\n")




@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Ferramenta de recuperação por assinatura."""
    if ctx.invoked_subcommand is None:
        _print_banner()
        _console.print("[yellow]Use [bold]garimpo scan --help[/bold] para começar.[/yellow]")




@main.command("scan")
@click.argument("image", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o", "--output", "output_dir",
    default="garimpo_output",
    show_default=True,
    type=click.Path(path_type=Path),
    help="Diretório de saída para arquivos recuperados e relatórios.",
)
@click.option(
    "-f", "--formats", "formats",
    default="",
    help=(
        "Lista de formatos a recuperar, separados por vírgula (ex.: jpeg,png,pdf). "
        "Deixe vazio para usar todos os plugins registrados."
    ),
)
@click.option(
    "-m", "--mode", "mode",
    type=click.Choice(["fast", "deep"], case_sensitive=False),
    default="fast",
    show_default=True,
    help=(
        "Modo de varredura. [bold]fast[/bold]: ignora artefatos corrompidos. "
        "[bold]deep[/bold]: mantém achados parciais/corrompidos e procura arquivos de texto."
    ),
)
@click.option(
    "--max-size", "max_size",
    default="100MB",
    show_default=True,
    help="Tamanho máximo por arquivo recuperado (ex.: 50MB, 1GB).",
)
@click.option(
    "--chunk-size", "chunk_size",
    default="64KB",
    show_default=True,
    help="Tamanho do bloco usado na leitura sequencial da imagem (ex.: 64KB, 1MB).",
)
@click.option(
    "--report", "report_format",
    type=click.Choice(["json", "csv", "all", "none"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Formato do relatório de evidências.",
)
@click.option(
    "--no-validate", "skip_validation",
    is_flag=True,
    default=False,
    help="Desativa a validação estrutural por formato (mais rápido, com mais falsos positivos).",
)
@click.option(
    "--no-hash", "skip_hashes",
    is_flag=True,
    default=False,
    help="Pula o cálculo de MD5/SHA-1/SHA-256 (mais rápido, sem verificação de integridade por hash).",
)
@click.option(
    "--no-dedup", "no_dedup",
    is_flag=True,
    default=False,
    help="Desativa a remoção de duplicados por SHA-256.",
)
@click.option(
    "--max-files", "max_files",
    default=0,
    type=int,
    show_default=True,
    help="Para depois de recuperar esta quantidade de arquivos (0 = sem limite).",
)
@click.option(
    "--log-level", "log_level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    show_default=True,
    help="Nível de detalhamento dos logs no console.",
)
@click.option(
    "--log-file", "log_file",
    default=None,
    type=click.Path(path_type=Path),
    help="Grava o log DEBUG completo neste arquivo (padrão: <saída>/garimpo_scan.log).",
)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Atalho para --log-level DEBUG.")
def cmd_scan(
    image: Path,
    output_dir: Path,
    formats: str,
    mode: str,
    max_size: str,
    chunk_size: str,
    report_format: str,
    skip_validation: bool,
    skip_hashes: bool,
    no_dedup: bool,
    max_files: int,
    log_level: str,
    log_file: Path | None,
    verbose: bool,
) -> None:
    """Varre uma imagem bruta e recupera arquivos encontrados."""
    _print_banner()


    try:
        max_size_bytes   = parse_size(max_size)
        chunk_size_bytes = parse_size(chunk_size)
    except ValueError as exc:
        _console.print(f"[red]Erro:[/red] {exc}")
        sys.exit(1)

    enabled_formats: list[str] = [f.strip() for f in formats.split(",") if f.strip()]


    for fmt in enabled_formats:
        if fmt not in FORMAT_ALIASES and fmt not in {p["extension"].lstrip(".") for p in list_plugin_info()}:
            _console.print(
                f"[yellow]Aviso:[/yellow] Formato desconhecido '{fmt}'. "
                "Use [bold]garimpo list-plugins[/bold] para ver os formatos disponíveis."
            )


    cfg = ScanConfig(
        image_path=image,
        output_dir=output_dir,
        chunk_size=chunk_size_bytes,
        max_file_size=max_size_bytes,
        mode=mode.lower(),
        enabled_formats=enabled_formats,
        validate=not skip_validation,
        compute_hashes=not skip_hashes,
        skip_duplicates=not no_dedup,
        max_carved_files=max_files,
        report_format=report_format,
        log_level="DEBUG" if verbose else log_level,
        log_file=log_file,
        verbose=verbose,
    )


    setup_logging(
        level=cfg.log_level,
        log_file=cfg.log_path,
        verbose=verbose,
    )


    _console.print(Panel(
        "\n".join([
            f"[bold]Imagem    :[/bold]  {image}",
            f"[bold]Saída     :[/bold]  {output_dir}",
            f"[bold]Modo      :[/bold]  {mode}",
            f"[bold]Tam. máx. :[/bold]  {human_size(max_size_bytes)} por arquivo",
            f"[bold]Formatos  :[/bold]  {', '.join(enabled_formats) or 'todos'}",
            f"[bold]Validar   :[/bold]  {'não' if skip_validation else 'sim'}",
            f"[bold]Hashes    :[/bold]  {'não' if skip_hashes else 'sim'}",
            f"[bold]Relatório :[/bold]  {report_format}",
        ]),
        title="[bold cyan]Configuração da varredura[/bold cyan]",
        border_style="cyan",
    ))


    t0 = time.perf_counter()
    engine = RecoveryEngine(cfg)

    try:
        session = engine.run()
    except ValueError as exc:
        _console.print(f"[red]Erro de configuração:[/red] {exc}")
        sys.exit(1)
    except PermissionError as exc:
        _console.print(f"[red]Permissão negada:[/red] {exc}")
        sys.exit(1)
    except OSError as exc:
        _console.print(f"[red]Erro de E/S:[/red] {exc}")
        sys.exit(1)

    elapsed = time.perf_counter() - t0


    if report_format != "none":
        try:
            report_files = write_reports(session, fmt=report_format)
        except Exception as exc:
            _console.print(f"[yellow]Falha ao gerar relatório:[/yellow] {exc}")
            report_files = []
    else:
        report_files = []


    rows = [
        f"[bold]Recuperados:[/bold]  [green]{len(session.results)}[/green] arquivo(s)",
        f"[bold]Ignorados  :[/bold]  {session.total_skipped} (baixa confiança / corrompido / duplicado)",
        f"[bold]Dados      :[/bold]  {human_size(session.total_bytes_recovered)} recuperados",
        f"[bold]Tempo      :[/bold]  {elapsed:.2f}s",
    ]
    if session.by_type:
        rows.append("[bold]Por tipo   :[/bold]")
        for ftype, count in sorted(session.by_type.items()):
            rows.append(f"  {ftype:<42} {count}")
    if report_files:
        rows.append("[bold]Relatórios :[/bold]")
        for p in report_files:
            rows.append(f"  {p}")

    _console.print(Panel(
        "\n".join(rows),
        title="[bold green]Recuperação concluída[/bold green]",
        border_style="green",
    ))




@main.command("list-plugins")
def cmd_list_plugins() -> None:
    """Lista os plugins disponíveis."""
    _print_banner()

    table = Table(
        title="Plugins registrados",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("Format", style="bold white", no_wrap=True)
    table.add_column("Extensão", style="cyan")
    table.add_column("Tipo MIME", style="dim")
    table.add_column("Cabeçalhos", justify="right")
    table.add_column("Rodapés", justify="right")
    table.add_column("Tam. máximo", justify="right")

    for p in list_plugin_info():
        table.add_row(
            p["name"],
            p["extension"],
            p["mime_type"],
            str(p["headers"]),
            str(p["footers"]),
            human_size(p["max_size"]),
        )

    _console.print(table)




@main.command("version")
def cmd_version() -> None:
    """Mostra versão e ambiente."""
    import platform as plat

    _console.print(Panel(
        "\n".join([
            f"[bold]Garimpo   :[/bold]  v{__version__}",
            f"[bold]Python    :[/bold]  {plat.python_version()}",
            f"[bold]Plataforma:[/bold]  {plat.system()} {plat.release()} ({plat.machine()})",
        ]),
        title="[bold cyan]Garimpo – Informações da versão[/bold cyan]",
        border_style="cyan",
    ))


@main.command("web")
@click.option("--host", default="127.0.0.1", show_default=True, help="Endereço do servidor web.")
@click.option("--port", default=5000, type=int, show_default=True, help="Porta do servidor web.")
@click.option(
    "--data-dir",
    default="garimpo_web_data",
    show_default=True,
    type=click.Path(path_type=Path),
    help="Diretório onde uploads, sessões e resultados web serão armazenados.",
)
def cmd_web(host: str, port: int, data_dir: Path) -> None:
    """Inicia a interface web local."""
    from garimpo.webapp import create_app

    _print_banner()
    _console.print(Panel(
        "\n".join([
            f"[bold]URL[/bold]        : http://{host}:{port}",
            f"[bold]Dados web[/bold]  : {data_dir}",
            "[bold]Modo[/bold]       : interface local com uploads e acompanhamento em tempo real",
        ]),
        title="[bold cyan]Garimpo Web[/bold cyan]",
        border_style="cyan",
    ))
    app = create_app(base_dir=data_dir)
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
