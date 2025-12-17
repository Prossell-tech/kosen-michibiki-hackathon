# DeckGL 色分けサンプル

このリポジトリは、DeckGLを使用して都道府県ごとに色分けされた地図を表示するサンプルコードを提供します。

![DeckGL Sample](../doc/color_tile.png)

## 必要環境

- Node.js

## インストール手順

1. Node.jsをインストールします。
[Node.js公式サイト](https://nodejs.org/)

2. ターミナルでプロジェクトディレクトリに移動し、依存関係をインストールします。

```bash
cd deckgl-sample
npm install
```

3. 環境変数を設定します。`.env`ファイルを作成し、以下の内容を追加します。

```bash
NEXT_PUBLIC_MAPBOX_TOKEN=あなたのMapboxAPIキー
```

4. 開発サーバーを起動します。

```bash
npm run dev
```
