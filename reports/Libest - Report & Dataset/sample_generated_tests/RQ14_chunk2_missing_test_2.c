/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ14_chunk2_missing_test_2.c
 */

static void rq14_chunk2_missing_test_2(void)
{
    EST_CTX *ectx = NULL;

    LOG_FUNC_NM;

    /*
     * Case A: Initialize without any CA/TA data. The API documentation
     * requires the application to provide local CA certificates; assert
     * that initializing with no CA chain fails (returns NULL).
     */
    ectx = est_client_init(NULL, 0, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ectx == NULL);

    /*
     * Case B: Initialize with the provided cacerts buffer (existing tests
     * demonstrate this should succeed). Assert non-NULL context and clean up.
     */
    ectx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, NULL);
    CU_ASSERT(ectx != NULL);

    if (ectx) {
        est_destroy(ectx);
    }
}
