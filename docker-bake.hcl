group "default" {
  targets = ["bot", "bot-asyncpg"]
}

target "docker-metadata-action" {}

target "_common" {
  inherits   = ["docker-metadata-action"]
  context    = "."
  dockerfile = "Dockerfile"
  platforms  = ["linux/arm64"]
  output     = ["type=cacheonly"]
}

target "bot" {
  inherits = ["_common"]
  args = {
    EXTRA_DEPENDENCIES = ""
  }
}

target "bot-asyncpg" {
  inherits = ["_common"]
  args = {
    EXTRA_DEPENDENCIES = "asyncpg"
  }
}
