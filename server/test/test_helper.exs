ExUnit.start(exclude: [:database])

# Only configure sandbox if database is available
try do
  Ecto.Adapters.SQL.Sandbox.mode(Server.Repo, :manual)
rescue
  DBConnection.ConnectionError ->
    # Database not available, tests tagged with :database will be excluded
    IO.puts("⚠️  Database not available, excluding database-dependent tests")
end
