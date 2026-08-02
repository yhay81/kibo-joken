import { readFileSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = process.cwd();
const index = JSON.parse(readFileSync(resolve(root, "public/data/index.json"), "utf8"));
const records = JSON.parse(readFileSync(resolve(root, "public/data/conditions.json"), "utf8"));
const find = (id: string) => records.find((record: { id: string }) => record.id === id);

describe("official company-size condition tables", () => {
  it("retains verified source metadata and the common boundary", () => {
    expect(index).toMatchObject({
      asOf: "2026-08-02",
      edition: "2025年度（令和7年度）",
      years: [2020, 2021, 2022, 2023, 2024, 2025],
      sizeCount: 8,
      recordCount: 8,
      employment: "パートタイムを除く常用",
    });
    expect(
      Object.fromEntries(
        index.sources.map((source: { metric: string; sha256: string }) => [
          source.metric,
          source.sha256,
        ]),
      ),
    ).toEqual({
      weekend: "508c96fbf5ce32b8041658d0092fec8f514f198fe056172b4a4be1b51ab0dd11",
      bonus: "65d7065b8201af4f8f71241bcf776e397bfd6b952922f5fe9ce4b56936528b01",
      commute: "745b6c73cda6352fc837917261a9c39aff81ac1eeb2dd601de3145d536465939",
    });
  });

  it("contains the total and seven unique size bands with six values per category", () => {
    expect(records).toHaveLength(8);
    expect(new Set(records.map((record: { id: string }) => record.id)).size).toBe(8);
    expect(records.map((record: { name: string }) => record.name)).toEqual([
      "企業規模計",
      "4人以下",
      "5〜29人",
      "30〜99人",
      "100〜299人",
      "300〜499人",
      "500〜999人",
      "1,000人以上",
    ]);
    for (const record of records) {
      for (const values of [
        record.weekend.total,
        record.weekend.complete,
        record.weekend.other,
        record.weekend.none,
        record.bonus.yes,
        record.bonus.no,
        record.commute.upperLimit,
        record.commute.noLimit,
        record.commute.fixed,
        record.commute.none,
      ])
        expect(values).toHaveLength(6);
    }
  });

  it("retains both ends of the 2025 company-size comparison", () => {
    expect(find("LE4")).toMatchObject({
      weekend: {
        total: expect.arrayContaining([56729]),
        complete: expect.arrayContaining([34120]),
      },
      bonus: { yes: expect.arrayContaining([153679]), no: expect.arrayContaining([66380]) },
    });
    expect(find("GE1000")).toMatchObject({
      weekend: {
        total: expect.arrayContaining([26514]),
        complete: expect.arrayContaining([19219]),
      },
      bonus: { yes: expect.arrayContaining([853004]), no: expect.arrayContaining([195269]) },
    });
  });

  it("retains the nationwide 2025 counts", () => {
    expect(find("ALL")).toMatchObject({
      weekend: {
        total: [
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          487753,
          467333,
        ],
        complete: [
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          275831,
          273456,
        ],
        none: [
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          9302,
          7915,
        ],
      },
      bonus: {
        yes: [
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          4703629,
          4557274,
        ],
        no: [
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          1021829,
          952076,
        ],
      },
      commute: {
        upperLimit: [
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          3799692,
          3647311,
        ],
        noLimit: [
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          1321467,
          1286082,
        ],
        fixed: [
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          142464,
          138168,
        ],
        none: [
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          expect.any(Number),
          461835,
          437789,
        ],
      },
    });
  });

  it("keeps every weekend row additive and every denominator positive", () => {
    for (const record of records)
      for (let year = 0; year < 6; year += 1) {
        expect(
          record.weekend.complete[year] + record.weekend.other[year] + record.weekend.none[year],
        ).toBe(record.weekend.total[year]);
        expect(record.bonus.yes[year] + record.bonus.no[year]).toBeGreaterThan(0);
        expect(
          record.commute.upperLimit[year] +
            record.commute.noLimit[year] +
            record.commute.fixed[year] +
            record.commute.none[year],
        ).toBeGreaterThan(0);
      }
  });

  it("keeps the company-size rows additive to the published total", () => {
    const total = find("ALL");
    const sizes = records.filter((record: { id: string }) => record.id !== "ALL");
    for (const [group, key] of [
      ["weekend", "total"],
      ["weekend", "complete"],
      ["weekend", "other"],
      ["weekend", "none"],
      ["bonus", "yes"],
      ["bonus", "no"],
      ["commute", "upperLimit"],
      ["commute", "noLimit"],
      ["commute", "fixed"],
      ["commute", "none"],
    ] as const)
      for (let year = 0; year < 6; year += 1)
        expect(
          sizes.reduce(
            (sum: number, record: Record<string, Record<string, number[]>>) =>
              sum + record[group][key][year],
            0,
          ),
        ).toBe(total[group][key][year]);
  });

  it("stays within the static delivery budget", () => {
    expect(statSync(resolve(root, "public/data/conditions.json")).size).toBeLessThan(20000);
  });
});
