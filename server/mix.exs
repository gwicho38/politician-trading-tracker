defmodule Server.MixProject do
  @moduledoc """
  Mix project configuration for the Politician Trading Tracker server.

  This is a minimal Phoenix API server that connects to Supabase PostgreSQL.
  """
  use Mix.Project

  def project do
    [
      app: :server,
      version: "0.1.0",
      elixir: "~> 1.14",
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      aliases: aliases(),
      deps: deps(),

      # Documentation
      name: "Politician Trading Server",
      docs: [main: "Server", extras: ["README.md"]]
    ]
  end

  def application do
    [
      mod: {Server.Application, []},
      extra_applications: [:logger, :runtime_tools]
    ]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  # Minimal dependencies for API server with Supabase PostgreSQL
  defp deps do
    [
      # Phoenix core (API only - no HTML/assets)
      {:phoenix, "~> 1.7.21"},
      {:bandit, "~> 1.5"},

      # Database (Ecto + PostgreSQL for Supabase)
      {:phoenix_ecto, "~> 4.5"},
      {:ecto_sql, "~> 3.10"},
      {:postgrex, ">= 0.0.0"},

      # JSON handling
      {:jason, "~> 1.2"},

      # Telemetry & monitoring
      {:telemetry_metrics, "~> 1.0"},
      {:telemetry_poller, "~> 1.0"},

      # HTTP client (for external API calls if needed)
      {:finch, "~> 0.13"},

      # Clustering (optional, for distributed deployments)
      {:dns_cluster, "~> 0.1.1"},

      # Cron scheduling
      {:quantum, "~> 3.5"},

      # CORS support
      {:corsica, "~> 2.1"},

      # Email (Swoosh with Resend adapter)
      {:swoosh, "~> 1.16"},
      {:hackney, "~> 1.9"},
      {:req, "~> 0.5"},

      # Test dependencies
      {:mox, "~> 1.0", only: :test}
    ]
  end

  defp aliases do
    [
      setup: ["deps.get", "ecto.setup"],
      "ecto.setup": ["ecto.create", "ecto.migrate", "run priv/repo/seeds.exs"],
      "ecto.reset": ["ecto.drop", "ecto.setup"],
      test: ["ecto.create --quiet", "ecto.migrate --quiet", "test"]
    ]
  end
end
