# Scripts

このディレクトリには、Lambda パッケージングやデプロイ補助のスクリプトを配置します。

## package_lambda.sh

Lambda デプロイ用 zip を作成します。

- 入力
	- `lambda_function.py`
	- `src/`
- 出力
	- `dist/line-bot-aws-iot-lambda.zip`

実行例:

```bash
./scripts/package_lambda.sh
```
