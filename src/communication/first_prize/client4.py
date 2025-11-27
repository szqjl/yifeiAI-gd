# -*- coding: utf-8 -*-
# 涓绛夊栦唬鐮 - client4
# 閫傞厤绂荤嚎骞冲彴锛堢鍙23456锛孶RL鏍煎紡/game/client4锛

import json
import sys
from pathlib import Path
from ws4py.client.threadedclient import WebSocketClient

# 娣诲姞first_prize鐩褰曞埌璺寰
sys.path.insert(0, str(Path(__file__).parent))
from state import State
from action import Action


class FirstPrizeClient4(WebSocketClient):

    def __init__(self, url):
        super().__init__(url)
        self.state = State("client4")
        self.action = Action("client4")

    def opened(self):
        print("[client4] Connected successfully!")

    def closed(self, code, reason=None):
        print(f"[client4] Closed down: {code}, {reason}")

    def received_message(self, message):
        try:
            message = json.loads(str(message))
            self.state.parse(message)
            if "actionList" in message:
                try:
                    act_index = self.action.rule_parse(
                        message,
                        self.state._myPos,
                        self.state.remain_cards,
                        self.state.history,
                        self.state.remain_cards_classbynum,
                        self.state.pass_num,
                        self.state.my_pass_num,
                        self.state.tribute_result
                    )
                    print(f"[client4] Act index: {act_index}")
                    self.send(json.dumps({"actIndex": act_index}))
                except Exception as e:
                    # 鍐崇瓥鍑洪敊鏃讹紝浣跨敤榛樿ゅ姩浣滐紙PASS锛
                    print(f"[client4] Decision error: {e}, using default action")
                    import traceback
                    traceback.print_exc()
                    try:
                        self.send(json.dumps({"actIndex": 0}))  # PASS
                    except:
                        pass
        except Exception as e:
            # 鎹曡幏鎵鏈夊紓甯革紝閬垮厤鏂寮杩炴帴
            print(f"[client4] Error processing message: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    try:
        # 绂荤嚎骞冲彴閰嶇疆锛堢鍙23456锛孶RL鏍煎紡/game/client4锛
        ws = FirstPrizeClient4('ws://127.0.0.1:23456/game/client4')
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()
    except Exception as e:
        print(f"[client4] Connection error: {e}")

