import { describe, it, expect } from "vitest";
import { resolveFeatures, CORE_FEATURES } from "./features";

const core = new Set(CORE_FEATURES);

describe("resolveFeatures — web mirror of api/app/features.py", () => {
  it("keeps core on even when unset", () => {
    expect(resolveFeatures(undefined)).toEqual(core);
    expect(resolveFeatures("")).toEqual(core);
  });

  it("adds declared features to core", () => {
    expect(resolveFeatures("cms,marketplace")).toEqual(
      new Set([...CORE_FEATURES, "cms", "marketplace"]),
    );
  });

  it("is case-insensitive and whitespace-tolerant", () => {
    expect(resolveFeatures("  CMS , Marketplace ,")).toEqual(
      new Set([...CORE_FEATURES, "cms", "marketplace"]),
    );
  });

  it("drops unknown keys without throwing", () => {
    expect(resolveFeatures("cms,banana")).toEqual(new Set([...CORE_FEATURES, "cms"]));
  });
});
