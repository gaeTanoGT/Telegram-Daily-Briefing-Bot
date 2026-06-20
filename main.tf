terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = "eu-south-1" # Milano. Cambia in "us-east-1" o "eu-central-1" se preferisci.
}

# --- 1. PREPARAZIONE DEL CODICE ---
# Questo blocco prende il tuo main.py e crea uno ZIP (AWS vuole solo zip)
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "main.py"
  output_path = "weather_payload.zip"
}

# --- 2. SICUREZZA (IAM) ---
# Creiamo un "Badge" (Ruolo) che la Lambda indosserà
resource "aws_iam_role" "iam_for_lambda" {
  name = "weather_notifier_role"

  # Trust Policy: Diciamo ad AWS "La Lambda ha il permesso di indossare questo badge"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Attacchiamo al badge il permesso di scrivere i Log (fondamentale per il debug!)
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- 3. LA FUNZIONE LAMBDA ---
resource "aws_lambda_function" "weather_lambda" {
  # Nome del file zip creato al punto 1
  filename      = "weather_payload.zip"
  
  # Nome della funzione che vedrai sulla console AWS
  function_name = "MeteoNotifier_Terraform"
  
  # Colleghiamo il Ruolo di sicurezza creato al punto 2
  role          = aws_iam_role.iam_for_lambda.arn
  
  # IMPORTANTE: NomeFile.NomeFunzioneDentroIlFile
  handler       = "main.lambda_handler"

  # Scegliamo una versione recente di Python
  runtime       = "python3.12"

  # Questo serve a Terraform per capire se hai modificato il codice Python
  # Se cambia l'hash, Terraform aggiornerà la Lambda
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  
  # Impostiamo un timeout di 10 secondi (il default è 3, a volte è poco per le API esterne)
  timeout = 15

  # configurazione telegram
  environment {
    variables = {
      TELEGRAM_TOKEN   = var.telegram_token
      TELEGRAM_CHAT_ID = var.telegram_chat_id
      OPENWEATHER_KEY  = var.openweather_key
      FINNHUB_KEY      = var.finnhub_key
    }
  }
}

# --- 4. L'AUTOMAZIONE (EventBridge) ---

# A. La "Sveglia" (Regola Temporale)
resource "aws_cloudwatch_event_rule" "morning_schedule" {
  name                = "weather_morning_trigger"
  description         = "Esegue la Lambda ogni mattina alle 7:00 UTC"
  
  # SINTASSI CRON: cron(Minuti Ore GiornoMese Mese GiornoSettimana Anno)
  # ATTENZIONE: AWS usa l'orario UTC (Londra). 
  # 07:00 UTC = 08:00 Italia (Inverno) / 09:00 Italia (Estate)
  schedule_expression = "cron(0 7 * * ? *)" 
}

# B. Il "Bersaglio" (Colleghiamo la sveglia alla Lambda)
resource "aws_cloudwatch_event_target" "target_lambda" {
  rule      = aws_cloudwatch_event_rule.morning_schedule.name
  target_id = "SendWeatherToLambda"
  arn       = aws_lambda_function.weather_lambda.arn
}

# C. Il Permesso (La Lambda deve accettare di essere svegliata da EventBridge)
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.weather_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.morning_schedule.arn
}

// --- 5. INTEGRAZIONE CON TELEGRAM ---
# creazione api gateway (l'intermediario con telegram)
resource "aws_apigatewayv2_api" "telegram_api" {
  name          = "telegram_webhook_api"
  protocol_type = "HTTP"
  description   = "API pubblica per ricevere messaggi da Telegram"
}

# integrazione api con la lambda
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.telegram_api.id
  integration_type = "AWS_PROXY" # Significa: "Passa tutto il pacchetto così com'è alla Lambda"
  
  integration_uri    = aws_lambda_function.weather_lambda.invoke_arn
  integration_method = "POST"
}

# la regola: se arriva una post, attiva integrazione
resource "aws_apigatewayv2_route" "post_route" {
  api_id    = aws_apigatewayv2_api.telegram_api.id
  route_key = "POST /" # Telegram usa sempre POST
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# attivazione auto deploy
resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.telegram_api.id
  name        = "$default"
  auto_deploy = true
}

# do permessi
resource "aws_lambda_permission" "api_gw_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.weather_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  
  # Questo blocca l'accesso solo alla TUA specifica API (Sicurezza)
  source_arn = "${aws_apigatewayv2_api.telegram_api.execution_arn}/*/*"
}

# stampo in output l'url dell'api gateway
output "webhook_url" {
  value = "${aws_apigatewayv2_stage.default_stage.invoke_url}"
  description = "L'URL pubblico da dare a Telegram"
}
