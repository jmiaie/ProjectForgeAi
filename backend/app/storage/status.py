from storage.locus_adapter import LocusAdapter
from storage.ompa_adapter import OmpaAdapter


def get_storage_status(project_id: str = "healthcheck") -> dict:
    locus = LocusAdapter(project_id)
    ompa = OmpaAdapter(project_id)
    return {
        "locus": locus.status(),
        "ompa": ompa.status(),
        "native_ready": locus.native and ompa.native,
    }
