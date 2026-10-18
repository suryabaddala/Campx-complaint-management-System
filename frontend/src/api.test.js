import { describe, expect, it } from "vitest";
import { messageFromError } from "./api";

describe("messageFromError", () => {
  it("uses the safe API error message when available", () => {
    expect(messageFromError({
      response: { data: { error: { message: "Please sign in again." } } },
    })).toBe("Please sign in again.");
  });

  it("falls back to a useful message for network errors", () => {
    expect(messageFromError({ message: "Network Error" })).toBe("Network Error");
  });

  it("does not show an empty error state", () => {
    expect(messageFromError(null)).toBe("Something went wrong. Please try again.");
  });
});
