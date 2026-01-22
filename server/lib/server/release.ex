defmodule Server.Release do
  @moduledoc """
  Used for executing DB release tasks when run in production without Mix
  installed.
  """
  @app :server

  # TODO: Review this function
  def migrate do
    load_app()

    for repo <- repos() do
      {:ok, _, _} = Ecto.Migrator.with_repo(repo, &Ecto.Migrator.run(&1, :up, all: true))
    end
  end

  # TODO: Review this function
  def rollback(repo, version) do
    load_app()
    {:ok, _, _} = Ecto.Migrator.with_repo(repo, &Ecto.Migrator.run(&1, :down, to: version))
  end

  # TODO: Review this function
  defp repos do
    Application.fetch_env!(@app, :ecto_repos)
  end

  # TODO: Review this function
  defp load_app do
    Application.load(@app)
  end
end
