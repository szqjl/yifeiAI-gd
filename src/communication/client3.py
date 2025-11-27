# -*- coding: utf-8 -*-
# @Time       : 2020/10/1 16:30
# @Author     : Duofeng Wu
# @File       : client.py
# @Description:

import json
from ws4py.client.threadedclient import WebSocketClient
from state import State
from action import Action


class ExampleClient(WebSocketClient):

    def __init__(self, url):
        super().__init__(url)
        self.state = State("client3")
        self.action = Action("client3")

    def opened(self):
        pass

    def closed(self, code, reason=None):
        print("Closed down", code, reason)

    def received_message(self, message):
        try:
            message = json.loads(str(message))                                    # 鍏堝簭鍒楀寲鏀跺埌鐨勬秷鎭锛岃浆涓篜ython涓鐨勫瓧鍏
            self.state.parse(message)                                             # 璋冪敤鐘舵佸硅薄鏉ヨВ鏋愮姸鎬
            if "actionList" in message:                                           # 闇瑕佸仛鍑哄姩浣滈夋嫨鏃惰皟鐢ㄥ姩浣滃硅薄杩涜岃В鏋
                try:
                    act_index = self.action.rule_parse(message,self.state._myPos,self.state.remain_cards,self.state.history,
                                                       self.state.remain_cards_classbynum,self.state.pass_num,
                                                       self.state.my_pass_num,self.state.tribute_result)
                    print(act_index)
                    self.send(json.dumps({"actIndex": act_index}))
                except Exception as e:
                    # 鍐崇瓥鍑洪敊鏃讹紝浣跨敤榛樿ゅ姩浣滐紙PASS锛
                    print(f"[client3] Decision error: {e}, using default action")
                    import traceback
                    traceback.print_exc()
                    try:
                        self.send(json.dumps({"actIndex": 0}))  # PASS
                    except:
                        pass
        except Exception as e:
            # 鎹曡幏鎵鏈夊紓甯革紝閬垮厤鏂寮杩炴帴
            print(f"[client3] Error processing message: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    try:
        # 淇鏀逛负绂荤嚎骞冲彴閰嶇疆锛堢鍙23456锛孶RL鏍煎紡/game/client3锛
        ws = ExampleClient('ws://127.0.0.1:23456/game/client3')
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()
