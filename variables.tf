variable "aws_region" {
  description = "Regione AWS target"
  type        = string
  default     = "eu-south-1"
}

variable "telegram_token" {
  description = "Token del Bot Telegram"
  type        = string
  sensitive   = true
}

variable "telegram_chat_id" {
  description = "Chat ID per la ricezione notifiche"
  type        = string
  sensitive   = true
}

variable "openweather_key" {
  description = "API Key di OpenWeatherMap"
  type        = string
  sensitive   = true
}

variable "finnhub_key" {
  description = "API Key di finnhub"
  type        = string
  sensitive   = true
}