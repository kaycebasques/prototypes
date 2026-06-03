#pragma once

#include "ping.rpc.pb.h"
#include "pw_log/log.h"

class PingService final
    : public rpc::ping::pw_rpc::nanopb::PingService::Service<PingService> {
 public:
  pw::Status Ping(const rpc_ping_PingRequest& request,
                  rpc_ping_PingResponse& response) {
    PW_LOG_INFO("Server received ping: %s", request.value);
    snprintf(response.value, sizeof(response.value), "Echo: %s", request.value);
    return pw::OkStatus();
  }
};
