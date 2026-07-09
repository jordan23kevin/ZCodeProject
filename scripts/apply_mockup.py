#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兼容旧用法的单文件入口。

功能与旧版 apply_white_t_mockup.py 保持一致，内部调用 white_t_mockup 包。
"""

from white_t_mockup.cli import main

if __name__ == "__main__":
    main()
