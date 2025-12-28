defmodule Server.Scheduler.Quantum do
  @moduledoc """
  Quantum-based cron scheduler implementation.

  This is the internal Quantum process. Use `Server.Scheduler` as the
  public entry point for job management.
  """

  use Quantum, otp_app: :server
end
