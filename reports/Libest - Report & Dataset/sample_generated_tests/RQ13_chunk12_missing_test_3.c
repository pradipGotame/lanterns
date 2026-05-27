/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk12_missing_test_3.c
 */

#include <CUnit/CUnit.h>
#include <stdlib.h>
#include "est.h"

/*
 * Shared prelude: CUnit include and EST API header.  The test below
 * follows the style of the exemplars (use of CU_ASSERT and EST APIs).
 */

static void rq13_chunk12_missing_test_3(void)
{
    EST_CTX *ectx = NULL;
    unsigned char *cacerts = NULL;
    int cacerts_len = 0;
    unsigned char *explicit_cacerts = NULL;
    int explicit_cacerts_len = 0;
    unsigned char *attr_data = NULL;
    int attr_len = 0;
    int rv = 0;

    /*
     * Read in a CA bundle that may contain explicit+implicit TAs
     * (exemplar style uses a project-provided filename constant).
     */
    cacerts_len = read_binary_file(CLIENT_UT_CACERT, &cacerts);
    CU_ASSERT(cacerts_len > 0);
    if (cacerts_len <= 0) {
        return;
    }

    /*
     * Initialize a client context with the combined TA set
     */
    ectx = est_client_init(cacerts, cacerts_len,
                           EST_CERT_FORMAT_PEM,
                           client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);
    if (!ectx) {
        free(cacerts);
        return;
    }

    /*
     * Verify a basic client operation succeeds with the initial TA set
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    if (rv == EST_ERR_NONE && attr_data) {
        free(attr_data);
        attr_data = NULL;
    }

    /*
     * Now read an explicit-only TA bundle to simulate disabling implicit TAs
     */
    explicit_cacerts_len = read_binary_file(US897_CACERTS_SINGLE_CHAIN_MULT_CERTS,
                                            &explicit_cacerts);
    CU_ASSERT(explicit_cacerts_len > 0);
    if (explicit_cacerts_len <= 0) {
        est_destroy(ectx);
        free(cacerts);
        return;
    }

    /*
     * Replace the client's trusted certs with the explicit-only set.
     * This exercises the library path that reloads the TA DB (see
     * supporting est_load_trusted_certs usage in exemplars).
     */
    rv = est_load_trusted_certs(ectx, explicit_cacerts, explicit_cacerts_len);
    CU_ASSERT(rv == EST_ERR_NONE);

    /*
     * After reloading the trusted certs (simulating implicit TA disablement),
     * verify the client can still perform a basic operation.  This shows the
     * client context accepted the new explicit-only TA DB and remains usable.
     */
    rv = est_client_get_csrattrs(ectx, &attr_data, &attr_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    if (rv == EST_ERR_NONE && attr_data) {
        free(attr_data);
        attr_data = NULL;
    }

    /*
     * Cleanup
     */
    est_destroy(ectx);
    free(cacerts);
    free(explicit_cacerts);
}
