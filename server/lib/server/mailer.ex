defmodule Server.Mailer do
  @moduledoc """
  Email delivery module using Swoosh.

  Supports Resend adapter for production email delivery.
  Falls back to Local adapter when RESEND_API_KEY is not configured.
  """
  use Swoosh.Mailer, otp_app: :server
end
