defmodule Server.JobsRepo do
  @moduledoc """
  Ecto Repo for the jobs schema in Supabase.

  This repo is specifically configured to work with the `jobs` schema
  for scheduled job management, including:
  - scheduled_jobs table
  - job_executions table

  The search_path is set to `jobs, public` via after_connect callback.
  """

  use Ecto.Repo,
    otp_app: :server,
    adapter: Ecto.Adapters.Postgres
end
