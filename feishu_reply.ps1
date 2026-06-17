$cli = "C:\Users\Jennifer\AppData\Roaming\npm\node_modules\@larksuite\cli\bin\lark-cli.exe"

& $cli event +subscribe --event-types im.message.receive_v1 --compact --quiet --as bot | ForEach-Object {
    try {
        $ev = $_ | ConvertFrom-Json
        $msgId = $ev.message_id
        $senderId = $ev.sender_id
        if ($msgId) {
            $replyJson = '{"msg_type":"text","content":"{\"text\":\"收到\"}"}'
            & $cli api POST "/open-apis/im/v1/messages/$msgId/reply" --data $replyJson --as bot --format json
        }
    } catch {
        # ignore parse errors
    }
}
