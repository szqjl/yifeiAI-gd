param(
    [Parameter(Mandatory=$true)]
    [string]$ChatId,
    [Parameter(Mandatory=$true)]
    [string]$Message
)

$ProfileName = "yife-gd-bot"

lark-cli im +messages-send --chat-id $ChatId --text $Message --profile $ProfileName --as bot
