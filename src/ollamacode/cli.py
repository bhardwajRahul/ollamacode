"""Main CLI interface for OllamaCode."""

import click
import sys
from rich.console import Console

from .interactive_session import InteractiveSession
from .config import Config
from .error_handler import handle_errors

console = Console()


@click.command()
@click.argument('initial_prompt', required=False)
@click.option('-p', '--prompt', help='Run in headless mode with the given prompt')
@click.option('-c', '--continue', 'continue_session', is_flag=True, help='Continue the last session')
@click.option('--model', help='Ollama model to use')
@click.option('--url', help='Ollama server URL') 
@click.option('--config-only', is_flag=True, help='Show configuration and exit')
@click.version_option()
@handle_errors
def main(initial_prompt, prompt, continue_session, model, url, config_only):
    """OllamaCode - AI-assisted coding with Ollama.
    
    An interactive AI coding assistant that runs locally using Ollama.
    Similar to Claude Code but powered by local models.
    
    Examples:
        ollamacode                           # Start interactive session
        ollamacode "help me fix this bug"    # Interactive with initial prompt
        ollamacode -p "explain this code"    # Headless mode
        cat file.py | ollamacode -p "review" # Process piped input
        ollamacode -c                        # Continue last session
    """
    
    if config_only:
        config = Config()
        console.print("[bold blue]OllamaCode Configuration[/bold blue]")
        console.print(config.show_config())
        return
    
    # Handle piped input
    piped_input = None
    if not sys.stdin.isatty():
        piped_input = sys.stdin.read().strip()
    
    # Start session
    session = InteractiveSession(model=model, url=url)
    
    if prompt:
        # Headless mode
        session.run_headless(prompt, piped_input)
    elif continue_session:
        # Continue last session
        session.continue_session()
    elif initial_prompt:
        # Interactive with initial prompt
        session.start(initial_prompt=initial_prompt)
    else:
        # Standard interactive mode
        session.start()


if __name__ == '__main__':
    main()