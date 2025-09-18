# みちびき利活用ハッカソン 講義3回目

## 講義内で使用したツール

- [VSCode](https://code.visualstudio.com/)
- [VSCode Serial Monitor](https://marketplace.visualstudio.com/items?itemName=ms-vscode.vscode-serial-monitor)

## 講義スライド

- [講義3回目スライド (PDF)](./lecture3.pdf)

## 講義テキスト

## 実際に取得したデータ

```nmea
$QZQSM,61,9AAD5C2AF9000128BFE2C23600000000000000000000000000000011F4043BC*0C
```

## Azarashiライブラリのインストール

- [Azarashiライブラリ](https://github.com/nbtk/azarashi)

```bash
pip install azarashi
echo
'$QZQSM,61,9AAD5C2AF9000128BFE2C236000000000000000000000
00000000011F4043BC*0C' | azarashi nmea
```

PowerShellの場合は次のように変更してください。

```powershell
'$QZQSM,61,9AAD5C2AF9000128BFE2C23600000000000000000000000000000011F4043BC*0C' | azarashi nmea
```

## ダミーパケット送信プログラム

[Simple DCR Emulator](../simple-dcr-emulator/README.md)

## 参考資料

- [パフォーマンススタンダード及びユーザインタフェース仕様書・性能評価結果](https://qzss.go.jp/technical/download/ps-is-qzss.html)
- [Azarashiライブラリ](https://github.com/nbtk/azarashi)
