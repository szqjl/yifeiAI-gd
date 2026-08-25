# -*- coding: utf-8 -*-
"""Pack the botzone submission zip.

Produces dist/fabledan_bot.zip with:
  __main__.py           (the bot entry)
  fabledan/*.py         (pure-python modules only, no torch)

Upload the zip on botzone as *python3* source code (扩展名 .zip 直接作为
python 源码上传, 平台支持 zip 包内 __main__.py 入口).
Model weights (fabledan_weights.npz) must be uploaded separately to your
botzone user storage space (用户存储空间), the bot reads 'data/fabledan_weights.npz'.
If --embed-weights is given, weights are embedded into the zip instead
(works if the zip stays within botzone's source size limit).

Usage:
    python botzone/pack_bot.py --weights ckpts/run1/best.npz
    python botzone/pack_bot.py --weights ckpts/run1/best.npz --embed-weights
"""

import argparse
import os
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BOT_MODULES = ["__init__.py", "cards.py", "combos.py", "engine.py",
               "encode.py", "model_np.py", "agents.py", "train_demo.py"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="")
    ap.add_argument("--embed-weights", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "fabledan_bot.zip"))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(HERE, "bot_fabledan.py"), "__main__.py")
        for m in BOT_MODULES:
            src = os.path.join(ROOT, "fabledan", m)
            z.write(src, "fabledan/" + m)
        if args.weights and args.embed_weights:
            z.write(args.weights, "fabledan_weights.npz")
    size = os.path.getsize(args.out)
    print("wrote %s (%.1f KB)" % (args.out, size / 1024))
    if args.weights and not args.embed_weights:
        dst = os.path.join(ROOT, "dist", "fabledan_weights.npz")
        shutil.copyfile(args.weights, dst)
        print("weights copied to %s -- upload this file to botzone 用户存储空间"
              % dst)


if __name__ == "__main__":
    main()
