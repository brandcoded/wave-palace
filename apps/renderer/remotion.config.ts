import { Config } from "@remotion/cli/config";

Config.setCodec("h264");
Config.setPixelFormat("yuv420p");
Config.setCrf(20);
Config.setOverwriteOutput(true);
Config.setScale(1);
