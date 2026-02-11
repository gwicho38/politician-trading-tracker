defmodule Server.Scheduler.Jobs.PoliticianTradingETLJob do
  @moduledoc """
  Config-driven factory for politician trading ETL job modules.

  Generates Elixir modules that implement `Server.Scheduler.Job` behaviour
  from configuration maps. All generated jobs POST to the Python ETL service's
  `/etl/trigger` endpoint with source-specific parameters.

  ## Usage

      configs = [
        %{job_id: "politician-trading-house", ...},
        %{job_id: "politician-trading-senate", ...},
      ]

      modules = PoliticianTradingETLJob.create_all(configs)
      # Returns list of generated module atoms

  ## Why a factory?

  The 5 politician trading jobs (House, Senate, QuiverQuant, EU, California)
  are 80-90% identical: they all POST to /etl/trigger with different `source`
  and `params`. This factory eliminates that duplication while keeping each
  job as a proper module that satisfies the Job behaviour.
  """

  require Logger

  @etl_service_url "https://politician-trading-etl.fly.dev"

  @doc """
  Creates all ETL job modules from a list of config maps.

  Each config map must have:
  - `:job_id` - unique identifier (e.g., "politician-trading-house")
  - `:job_name` - human-readable name
  - `:source` - ETL source identifier (e.g., "house", "senate", "quiverquant")
  - `:schedule` - cron expression
  - `:params` - map of additional params to send with the trigger request

  Returns a list of the created module atoms.
  """
  def create_all(configs) when is_list(configs) do
    Enum.map(configs, &create_job_module/1)
  end

  @doc """
  Creates a single ETL job module from a config map.

  Uses `Module.create/3` to generate a module that implements the
  `Server.Scheduler.Job` behaviour. The module delegates to the shared
  `trigger_etl/2` function for the actual HTTP call.

  Returns the module atom.
  """
  def create_job_module(config) do
    %{
      job_id: job_id,
      job_name: job_name,
      source: source,
      schedule: schedule,
      params: params
    } = config

    # Generate a unique module name from the job_id
    # e.g., "politician-trading-house" -> Server.Scheduler.Jobs.ETL.PoliticianTradingHouse
    module_suffix =
      job_id
      |> String.split("-")
      |> Enum.map(&String.capitalize/1)
      |> Enum.join()

    module_name = Module.concat(Server.Scheduler.Jobs.ETL, module_suffix)

    # Capture values for the quoted expression
    captured_job_id = job_id
    captured_job_name = job_name
    captured_source = source
    captured_schedule = schedule
    captured_params = params

    contents =
      quote do
        @behaviour Server.Scheduler.Job

        require Logger

        @impl true
        def job_id, do: unquote(captured_job_id)

        @impl true
        def job_name, do: unquote(captured_job_name)

        @impl true
        def schedule, do: unquote(captured_schedule)

        @impl true
        def run do
          Logger.info("[#{unquote(captured_job_name)}] Triggering ETL for source: #{unquote(captured_source)}")

          case Server.Scheduler.Jobs.PoliticianTradingETLJob.trigger_etl(
                 unquote(captured_source),
                 unquote(Macro.escape(captured_params))
               ) do
            {:ok, etl_job_id} ->
              Logger.info("[#{unquote(captured_job_name)}] ETL job started: #{etl_job_id}")
              {:ok, etl_job_id}

            {:error, reason} ->
              Logger.error("[#{unquote(captured_job_name)}] ETL trigger failed: #{inspect(reason)}")
              {:error, reason}
          end
        end

        @impl true
        def metadata do
          %{
            description: unquote(captured_job_name),
            etl_service: unquote(@etl_service_url),
            source: unquote(captured_source),
            params: unquote(Macro.escape(captured_params))
          }
        end
      end

    Module.create(module_name, contents, Macro.Env.location(__ENV__))
    Logger.debug("[ETLJobFactory] Created module: #{module_name}")
    module_name
  end

  @doc """
  Triggers an ETL job by POSTing to the Python ETL service.

  This is the shared HTTP trigger used by all generated job modules.
  Sends a POST request to /etl/trigger with the source and params.

  Returns `{:ok, job_id}` or `{:error, reason}`.
  """
  def trigger_etl(source, params) do
    url = "#{@etl_service_url}/etl/trigger"

    # Build request body: merge source with params, resolve dynamic values
    body_params = resolve_dynamic_params(params)
    body = Jason.encode!(Map.put(body_params, :source, source))

    headers = [
      {"Content-Type", "application/json"},
      {"Accept", "application/json"}
    ]

    headers =
      case Application.get_env(:server, :api_key) do
        nil -> headers
        key -> [{"X-API-Key", key} | headers]
      end

    request = Finch.build(:post, url, headers, body)

    case Finch.request(request, Server.Finch, receive_timeout: 30_000) do
      {:ok, %Finch.Response{status: 200, body: response_body}} ->
        case Jason.decode(response_body) do
          {:ok, %{"job_id" => job_id}} ->
            {:ok, job_id}

          {:ok, _response} ->
            {:ok, "unknown"}

          {:error, decode_error} ->
            {:error, {:decode_error, decode_error}}
        end

      {:ok, %Finch.Response{status: status, body: response_body}} ->
        {:error, {:http_error, status, response_body}}

      {:error, reason} ->
        {:error, {:request_failed, reason}}
    end
  end

  @doc false
  def resolve_dynamic_params(params) do
    Enum.reduce(params, %{}, fn {key, value}, acc ->
      resolved =
        case value do
          :current_year -> Date.utc_today().year
          other -> other
        end

      Map.put(acc, key, resolved)
    end)
  end
end
