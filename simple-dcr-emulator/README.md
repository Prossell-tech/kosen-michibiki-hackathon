# シンプル災危通報ダミーパケット送信プログラム

QZ1受信機のデータに災害時の災危通報を模擬的に付加して送信するプログラムです。
QZQSM形式のパケットをWebSocket経由で送信します。

## How to Use

1. Python3をインストール
2. 必要なライブラリをインストール

    ```bash
    pip install -r requirements.txt
    ```

3. QZ1受信機をPCに接続

4. main.pyのSERIAL_PORTを接続したポートに変更

    ```python
    SERIAL_PORT = "/dev/tty.usbserial-0001"  # 例: Windows "COM3", macOS "/dev/tty.usbserial-0001"
    ```

5. 実行

    ```bash
    python3 main.py
    ```

6. 載せる災害の種類を選択

    ```txt
    Select a dummy QZQSM message:
    1. (試験/訓練) 2019年11月27日18時10分 和歌山県南方沖 M9.0
    2. (発表) 2019年2月21日21時22分 胆振地方中東部 M5.8
    3. (発表) 2019年12月26日18時29分 宮城県沖 深さ50km M4.6
    4. (発表) 2022年8月26日08時48分 天草灘 深さ10km M4.6
    5. (訂正) 2019年11月15日01時18分 インドネシア付近 深さ不明 M7.1
    6. (発表) 2019年10月12日18時23分 千葉県 震度4
    7. (発表) 2022年8月26日08時48分 鹿児島県 震度4
    8. (試験/訓練) 大津波警報 2019年11月27日18時10分
    9. (発表) 津波警報 2022年1月16日 トンガ火山噴火
    10. (解除) 津波警報 2022年1月16日 トンガ火山噴火
    Enter number (1-10): 1
    Selected: (試験/訓練) 2019年11月27日18時10分 和歌山県南方沖 M9.0
    ```

7. 配信されているデータのソケットに接続して受信

### macOS場合

```bash
brew install websocat
websocat ws://localhost:8765
```

### Windows場合

 [websocatのリリースページ](https://github.com/vi/websocat/releases)
からwebsocatを導入するか、wscat等の他のWebSocketクライアントを使用してください。
