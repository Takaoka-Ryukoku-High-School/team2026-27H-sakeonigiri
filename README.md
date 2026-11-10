# Daily Note

Python と Flet で作った、ブラウザで使える日付表示アプリです。日本語・英語・中国語を切り替えて表示でき、富山県内の住所から国土地理院の公開データを使って近い指定避難所を検索できます。距離は直線距離で、避難所の開設状況は表示しません。

## 起動方法

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

起動するとブラウザでアプリが開きます。