import boto3
from rich.console import Console
from rich.progress import Progress

console = Console()

def get_exact_count(profile_name, table_name, region="us-east-1"):
    session = boto3.Session(profile_name=profile_name)
    dynamodb = session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    total_count = 0
    scanned_count = 0
    
    console.print(f"[bold blue]Starting exact count for table:[/bold blue] {table_name}")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Scanning items...", total=None)
        
        # Initial scan
        response = table.scan(Select='COUNT')
        total_count += response['Count']
        scanned_count += response['ScannedCount']
        progress.update(task, advance=response['Count'])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                Select='COUNT', 
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            total_count += response['Count']
            scanned_count += response['ScannedCount']
            progress.update(task, advance=response['Count'])

    return total_count, scanned_count

if __name__ == "__main__":
    PROFILE = "bench-dynamo"
    TABLE = "gtfs" # Account B table name
    
    try:
        count, scanned = get_exact_count(PROFILE, TABLE)
        console.print(f"\n[bold green]Success![/bold green]")
        console.print(f"Total Items: [bold white]{count:,}[/bold white]")
        console.print(f"Scanned Items: [dim]{scanned:,}[/dim] (includes filtered items if any)")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
