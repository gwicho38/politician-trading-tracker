defmodule ServerWeb do
  @moduledoc """
  Web interface module for the Politician Trading Tracker API.

  This module provides macros for defining controllers and routers.
  Use it in your modules like:

      use ServerWeb, :controller
      use ServerWeb, :router

  ## API-Only Design

  This server is designed as a JSON API backend. It does not include:
  - HTML rendering
  - LiveView
  - Asset compilation

  All endpoints return JSON responses.
  """

  # TODO: Review this function
  def static_paths, do: ~w(favicon.ico robots.txt)

  # TODO: Review this function
  def router do
    quote do
      use Phoenix.Router, helpers: false

      import Plug.Conn
      import Phoenix.Controller
    end
  end

  # TODO: Review this function
  def channel do
    quote do
      use Phoenix.Channel
    end
  end

  # TODO: Review this function
  def controller do
    quote do
      use Phoenix.Controller, formats: [:json]

      import Plug.Conn

      unquote(verified_routes())
    end
  end

  # TODO: Review this function
  def verified_routes do
    quote do
      use Phoenix.VerifiedRoutes,
        endpoint: ServerWeb.Endpoint,
        router: ServerWeb.Router,
        statics: ServerWeb.static_paths()
    end
  end

  @doc """
  Dispatches to the appropriate module based on the usage type.
  """
  defmacro __using__(which) when is_atom(which) do
    apply(__MODULE__, which, [])
  end
end
