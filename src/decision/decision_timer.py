# -*- coding: utf-8 -*-
"""
閸愬磭鐡ョ拋鈩冩傞崳銊δ侀崸 (Decision Timer)
閸旂喕鍏橀敍
- 閹貉冨煑閸愬磭鐡ラ弮鍫曟？
- 闂冨弶銏ｇТ閺
"""

import time
from typing import Optional


class DecisionTimer:
    """閸愬磭鐡ョ拋鈩冩傞崳"""
    
    def __init__(self, max_time: float = 0.8):
        """
        閸掓繂瀣瀵茬拋鈩冩傞崳
        
        Args:
            max_time: 閺堟径褍鍠呯粵鏍ㄦ傞梻杈剧礄缁夋帪绱氶敍宀勭帛鐠0.8缁
        """
        self.max_time = max_time
        self.start_time: Optional[float] = None
    
    def start(self):
        """瀵婵瀣鈩冩"""
        self.start_time = time.time()
    
    def check_timeout(self) -> bool:
        """
        濡閺屻儲妲搁崥锕佺Т閺
        
        Returns:
            婵″倹鐏夌搾鍛妞傛潻鏂挎礀True閿涘苯鎯侀崚娆掔箲閸ユ楷alse
        """
        if self.start_time is None:
            return False
        
        elapsed = time.time() - self.start_time
        return elapsed >= self.max_time
    
    def get_elapsed_time(self) -> float:
        """
        閼惧嘲褰囧歌尙鏁ら弮鍫曟？
        
        Returns:
            瀹歌尙鏁ら弮鍫曟？閿涘牏鎺炵礆
        """
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
    
    def get_remaining_time(self) -> float:
        """
        閼惧嘲褰囬崜鈺缍戦弮鍫曟？
        
        Returns:
            閸撯晙缍戦弮鍫曟？閿涘牏鎺炵礆
        """
        if self.start_time is None:
            return self.max_time
        elapsed = self.get_elapsed_time()
        return max(0.0, self.max_time - elapsed)
    
    def reset(self):
        """闁插秶鐤嗙拋鈩冩傞崳"""
        self.start_time = None

